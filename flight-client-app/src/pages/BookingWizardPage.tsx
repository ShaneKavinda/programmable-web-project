import AddIcon from "@mui/icons-material/Add";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import PersonIcon from "@mui/icons-material/Person";
import RemoveIcon from "@mui/icons-material/Remove";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiErrorSnackbar } from "../components/ApiErrorSnackbar";
import { useAuth } from "../context/AuthContext";
import { formatDateTimeDdMmYyyy } from "../lib/formatDate";
import { pickUniqueAvailableSeats } from "../lib/pickSeats";
import { createBooking } from "../services/bookings";
import { issueTokenByUserId } from "../services/auth";
import type { Flight, PassengerInput } from "../types";

const STEPS = ["Flight", "Passengers", "Review"];

type PassengerDraft = {
  passenger_fname: string;
  passenger_lname: string;
  email: string;
  passenger_passport_num: string;
  seat_class: PassengerInput["seat_class"];
};

const emptyPassenger = (): PassengerDraft => ({
  passenger_fname: "",
  passenger_lname: "",
  email: "",
  passenger_passport_num: "",
  seat_class: "economy",
});

const formatPrice = (value: number | string) => Number(value).toFixed(2);
const PRICE_MULTIPLIERS: Record<PassengerInput["seat_class"], number> = {
  economy: 1,
  business: 2.5,
  first: 4,
};

export const BookingWizardPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const { setAuth } = useAuth();

  const flight = location.state?.flight as Flight | undefined;

  const [activeStep, setActiveStep] = useState(0);
  const [passengers, setPassengers] = useState<PassengerDraft[]>([emptyPassenger(), emptyPassenger()]);
  const [assignedSeats, setAssignedSeats] = useState<string[]>([]);
  const [passengerError, setPassengerError] = useState<string | null>(null);
  const [seatPickError, setSeatPickError] = useState<string | null>(null);
  const [isPickingSeats, setIsPickingSeats] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState<{
    userId: string | null;
    bookingId: string;
  } | null>(null);

  useEffect(() => {
    if (!flight?.id) {
      navigate("/flights", { replace: true });
    }
  }, [flight, navigate]);

  const bookingMutation = useMutation({
    mutationFn: async () => {
      if (!flight) throw new Error("No flight selected.");
      if (assignedSeats.length !== passengers.length) {
        throw new Error("Seats are not assigned yet. Go back one step.");
      }
      const payload: PassengerInput[] = passengers.map((p, i) => ({
        passenger_fname: p.passenger_fname.trim(),
        passenger_lname: p.passenger_lname.trim(),
        email: p.email.trim() || undefined,
        passenger_passport_num: p.passenger_passport_num.trim(),
        seat_num: assignedSeats[i],
        seat_class: p.seat_class,
      }));
      return createBooking({
        flight_id: flight.id,
        passengers: payload,
      });
    },
    onSuccess: async (booking) => {
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      const userId = booking.user_id?.trim() ?? null;
      if (userId) {
        try {
          const auth = await issueTokenByUserId(userId);
          setAuth(auth.token, auth.user);
        } catch {
          // Keep booking creation successful even if token bootstrap fails.
        }
      }
      setBookingSuccess({
        userId,
        bookingId: String(booking.id),
      });
    },
  });

  const closeSuccessAndGoToBookings = () => {
    setBookingSuccess(null);
    navigate("/bookings", { replace: true });
  };

  const validatePassengers = (): boolean => {
    setPassengerError(null);
    for (let i = 0; i < passengers.length; i += 1) {
      const p = passengers[i];
      if (!p.passenger_fname.trim()) {
        setPassengerError(`Passenger ${i + 1}: first name is required.`);
        return false;
      }
      if (!p.passenger_lname.trim()) {
        setPassengerError(`Passenger ${i + 1}: last name is required.`);
        return false;
      }
      if (p.passenger_fname.trim().length > 50 || p.passenger_lname.trim().length > 50) {
        setPassengerError(`Passenger ${i + 1}: first/last name is too long (max 50).`);
        return false;
      }
      if (!p.passenger_passport_num.trim()) {
        setPassengerError(`Passenger ${i + 1}: passport number is required.`);
        return false;
      }
      if (p.passenger_passport_num.trim().length > 12) {
        setPassengerError(`Passenger ${i + 1}: passport number is too long (max 12).`);
        return false;
      }
      const email = p.email.trim();
      if (i === 0 && !email) {
        setPassengerError("Traveler 1: email is required for booking ownership.");
        return false;
      }
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setPassengerError(`Passenger ${i + 1}: enter a valid email.`);
        return false;
      }
    }
    return true;
  };

  const handleNext = async () => {
    if (activeStep === 0) {
      setActiveStep(1);
      return;
    }
    if (activeStep === 1) {
      if (!validatePassengers() || !flight) return;
      setSeatPickError(null);
      setIsPickingSeats(true);
      try {
        const seats = await pickUniqueAvailableSeats(flight.id, passengers.length);
        setAssignedSeats(seats);
        setActiveStep(2);
      } catch (e) {
        setSeatPickError(e instanceof Error ? e.message : "Could not assign seats.");
      } finally {
        setIsPickingSeats(false);
      }
    }
  };

  const handleBack = () => {
    if (activeStep === 2) {
      setAssignedSeats([]);
      setSeatPickError(null);
    }
    setActiveStep((s) => Math.max(0, s - 1));
  };

  const addPassenger = () => {
    if (passengers.length >= 10) return;
    setPassengers((prev) => [...prev, emptyPassenger()]);
  };

  const removePassenger = (index: number) => {
    if (passengers.length <= 1) return;
    setPassengers((prev) => prev.filter((_, i) => i !== index));
  };

  const updatePassenger = (index: number, patch: Partial<PassengerDraft>) => {
    setPassengers((prev) => prev.map((p, i) => (i === index ? { ...p, ...patch } : p)));
  };

  const reviewSummary = useMemo(() => {
    if (!flight) return null;
    const basePrice = Number(flight.base_price);
    return passengers.map((p, i) => ({
      label: `${p.passenger_fname.trim()} ${p.passenger_lname.trim()}`.trim() || `Passenger ${i + 1}`,
      email: p.email.trim() || "—",
      passport: p.passenger_passport_num.trim(),
      seat_class: p.seat_class,
      seat: assignedSeats[i] ?? "—",
      ticket_price: basePrice * PRICE_MULTIPLIERS[p.seat_class],
    }));
  }, [flight, passengers, assignedSeats]);

  const reviewTotalPrice = useMemo(() => {
    if (!reviewSummary) return 0;
    return reviewSummary.reduce((sum, row) => sum + row.ticket_price, 0);
  }, [reviewSummary]);

  if (!flight) {
    return null;
  }

  return (
    <Stack spacing={3} maxWidth={720} sx={{ mx: "auto" }}>
      <Dialog
        open={Boolean(bookingSuccess)}
        onClose={(_event, reason) => {
          if (reason === "backdropClick") return;
          closeSuccessAndGoToBookings();
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Booking confirmed</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Typography variant="body1">
              Your booking was created successfully. You are signed in and can open My Bookings.
            </Typography>
            {bookingSuccess?.userId ? (
              <>
                <Alert severity="info">
                  Save your user ID — you will need it on the Access Account page if you sign out or use another
                  browser.
                </Alert>
                <Typography variant="caption" color="text.secondary">
                  User ID
                </Typography>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 1,
                    bgcolor: "action.hover",
                    border: 1,
                    borderColor: "divider",
                    fontFamily: "monospace",
                    fontSize: "0.85rem",
                    wordBreak: "break-all",
                  }}
                >
                  <Tooltip title="Click to copy">
                    <span
                      style={{ cursor: "pointer" }}
                      role="button"
                      tabIndex={0}
                      onClick={() => navigator.clipboard?.writeText(bookingSuccess.userId!)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          navigator.clipboard?.writeText(bookingSuccess.userId!);
                        }
                      }}
                    >
                      {bookingSuccess.userId}
                    </span>
                  </Tooltip>
                </Box>
              </>
            ) : (
              <Alert severity="warning">
                No user ID was returned for this booking. You can still use My Bookings while this session is active, or
                use Access Account if you have your user ID from elsewhere.
              </Alert>
            )}
            <Typography variant="body2" color="text.secondary">
              Booking reference:{" "}
              <Box component="span" sx={{ fontFamily: "monospace" }}>
                {bookingSuccess?.bookingId}
              </Box>
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button variant="contained" onClick={closeSuccessAndGoToBookings}>
            Go to my bookings
          </Button>
        </DialogActions>
      </Dialog>

      <ApiErrorSnackbar error={bookingMutation.error} />
      <Typography variant="h5" fontWeight={700}>
        New booking
      </Typography>

      <Stepper activeStep={activeStep} alternativeLabel>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {activeStep === 0 && (
        <Card elevation={2}>
          <CardContent>
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <FlightTakeoffIcon color="primary" />
              <Typography variant="h6" fontWeight={700}>
                {flight.flight_code}
              </Typography>
              <Chip size="small" label={flight.status} />
            </Stack>
            <Typography>
              {flight.origin_airport} → {flight.destination_airport}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Departure: {formatDateTimeDdMmYyyy(flight.departure_time)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Arrival: {formatDateTimeDdMmYyyy(flight.arrival_time)}
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Typography fontWeight={700}>Base price (economy): EUR {formatPrice(flight.base_price)}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Add one or more travelers (for example yourself and a companion). Each traveler gets a ticket on the same
              booking. Cabin class and pricing follow your API rules. Seats are chosen automatically using the
              availability endpoint before you confirm.
            </Typography>
          </CardContent>
        </Card>
      )}

      {activeStep === 1 && (
        <Stack spacing={2}>
          <Typography variant="subtitle1" color="text.secondary">
            Enter each traveler&apos;s details. One booking can include multiple tickets (e.g. you and your partner).
          </Typography>
          {passengerError && <Alert severity="warning">{passengerError}</Alert>}
          {seatPickError && <Alert severity="error">{seatPickError}</Alert>}
          {isPickingSeats && (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={22} />
              <Typography variant="body2">Finding available seats…</Typography>
            </Stack>
          )}
          {passengers.map((p, index) => (
            <Card key={index} variant="outlined">
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <PersonIcon color="action" />
                    <Typography fontWeight={700}>Traveler {index + 1}</Typography>
                  </Stack>
                  {passengers.length > 1 && (
                    <Button
                      size="small"
                      color="inherit"
                      startIcon={<RemoveIcon />}
                      onClick={() => removePassenger(index)}
                      disabled={isPickingSeats}
                    >
                      Remove
                    </Button>
                  )}
                </Stack>
                <Stack spacing={2}>
                  <TextField
                    required
                    label="First name"
                    value={p.passenger_fname}
                    onChange={(e) => updatePassenger(index, { passenger_fname: e.target.value })}
                    fullWidth
                    disabled={isPickingSeats}
                  />
                  <TextField
                    required
                    label="Last name"
                    value={p.passenger_lname}
                    onChange={(e) => updatePassenger(index, { passenger_lname: e.target.value })}
                    fullWidth
                    disabled={isPickingSeats}
                  />
                  <TextField
                    required={index === 0}
                    label={index === 0 ? "Email (required for owner)" : "Email (optional)"}
                    type="email"
                    value={p.email}
                    onChange={(e) => updatePassenger(index, { email: e.target.value })}
                    fullWidth
                    disabled={isPickingSeats}
                  />
                  <TextField
                    required
                    label="Passport number"
                    value={p.passenger_passport_num}
                    onChange={(e) => updatePassenger(index, { passenger_passport_num: e.target.value })}
                    inputProps={{ maxLength: 12 }}
                    fullWidth
                    disabled={isPickingSeats}
                    helperText="As on the travel document (max 12 characters)"
                  />
                  <FormControl fullWidth disabled={isPickingSeats}>
                    <InputLabel id={`seat-class-${index}`}>Cabin class</InputLabel>
                    <Select
                      labelId={`seat-class-${index}`}
                      label="Cabin class"
                      value={p.seat_class}
                      onChange={(e) =>
                        updatePassenger(index, { seat_class: e.target.value as PassengerInput["seat_class"] })
                      }
                    >
                      <MenuItem value="economy">Economy</MenuItem>
                      <MenuItem value="business">Business</MenuItem>
                      <MenuItem value="first">First</MenuItem>
                    </Select>
                  </FormControl>
                </Stack>
              </CardContent>
            </Card>
          ))}
          {passengers.length < 10 && (
            <Button startIcon={<AddIcon />} variant="outlined" onClick={addPassenger} disabled={isPickingSeats}>
              Add another traveler
            </Button>
          )}
        </Stack>
      )}

      {activeStep === 2 && reviewSummary && (
        <Stack spacing={2}>
          <Typography variant="subtitle1">Review and confirm</Typography>
          <Typography variant="body2" color="text.secondary">
            Seats below were checked with the seat availability API. Confirm to create the booking.
          </Typography>
          <Card variant="outlined">
            <CardContent>
              <Typography fontWeight={700} gutterBottom>
                {flight.flight_code} · {flight.origin_airport} → {flight.destination_airport}
              </Typography>
              <Divider sx={{ my: 2 }} />
              {reviewSummary.map((row, i) => (
                <Box key={i} sx={{ mb: i < reviewSummary.length - 1 ? 2 : 0 }}>
                  <Typography fontWeight={600}>{row.label}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Passport: {row.passport} · {row.seat_class} · Seat {row.seat}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Email: {row.email}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Ticket price: EUR {formatPrice(row.ticket_price)}
                  </Typography>
                </Box>
              ))}
              <Divider sx={{ my: 2 }} />
              <Typography variant="h6" fontWeight={700}>
                Final total: EUR {formatPrice(reviewTotalPrice)}
              </Typography>
            </CardContent>
          </Card>
          <Button
            variant="contained"
            size="large"
            onClick={() => bookingMutation.mutate()}
            disabled={bookingMutation.isPending}
          >
            {bookingMutation.isPending ? "Creating booking…" : "Confirm booking"}
          </Button>
        </Stack>
      )}

      <Stack direction="row" spacing={2} justifyContent="space-between">
        <Button disabled={activeStep === 0 || isPickingSeats || bookingMutation.isPending} onClick={handleBack}>
          Back
        </Button>
        <Stack direction="row" spacing={1}>
          <Button onClick={() => navigate("/flights")} disabled={isPickingSeats || bookingMutation.isPending}>
            Cancel
          </Button>
          {activeStep < 2 && (
            <Button variant="contained" onClick={() => void handleNext()} disabled={isPickingSeats}>
              {activeStep === 1 ? (isPickingSeats ? "Working…" : "Next") : "Next"}
            </Button>
          )}
        </Stack>
      </Stack>
    </Stack>
  );
};
