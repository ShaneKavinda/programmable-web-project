import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ApiErrorSnackbar } from "../components/ApiErrorSnackbar";
import { clearAdminApiKey, getAdminApiKey, setAdminApiKey } from "../lib/adminApiKey";
import { formatDateTimeDdMmYyyy } from "../lib/formatDate";
import { getUsersPage } from "../services/auth";
import { getAuxLogs } from "../services/auxLogs";
import { createFlight, deleteFlight, searchAllFlights, searchFlightsPaginated, updateFlight } from "../services/flights";

const toApiDateTime = (value: string) => value.replace("T", " ") + ":00";

function apiDateTimeToLocalInput(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export const AdminPanelPage = () => {
  const queryClient = useQueryClient();
  const [adminApiKeyInput, setAdminApiKeyInput] = useState(getAdminApiKey() ?? "");
  const [activeAdminApiKey, setActiveAdminApiKey] = useState<string | null>(getAdminApiKey());
  const [editingFlightId, setEditingFlightId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    "all" | "active" | "inactive" | "started" | "en_route" | "landed" | "cancelled" | "delayed"
  >("all");
  const [codeFilter, setCodeFilter] = useState("");
  const [flightPage, setFlightPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [usersPage, setUsersPage] = useState(0);
  const [usersRowsPerPage, setUsersRowsPerPage] = useState(10);
  const [sortBy, setSortBy] = useState<"departure_time" | "arrival_time" | "base_price">("departure_time");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [editPrice, setEditPrice] = useState<string>("");
  const [editDeparture, setEditDeparture] = useState<string>("");
  const [editArrival, setEditArrival] = useState<string>("");
  const [editStatus, setEditStatus] = useState<
    "active" | "inactive" | "started" | "en_route" | "landed" | "cancelled" | "delayed"
  >("active");
  const [newFlight, setNewFlight] = useState({
    flight_code: "",
    origin_airport: "",
    destination_airport: "",
    departure_time: "",
    arrival_time: "",
    base_price: "",
  });
  const [bookingFilterInput, setBookingFilterInput] = useState("");
  const [bookingFilter, setBookingFilter] = useState("");
  const [limitInput, setLimitInput] = useState("50");

  const parsedLimit = useMemo(() => {
    const n = Number(limitInput);
    if (!Number.isFinite(n) || n < 1) return 50;
    return Math.min(200, Math.floor(n));
  }, [limitInput]);

  const flightsQuery = useQuery({
    queryKey: ["admin-flights", activeAdminApiKey, statusFilter, flightPage, rowsPerPage, sortBy, sortOrder],
    queryFn: () =>
      searchFlightsPaginated({
        page: flightPage + 1,
        per_page: rowsPerPage,
        status: statusFilter === "all" ? undefined : statusFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: Boolean(activeAdminApiKey),
  });
  const codeFilterTrimmed = codeFilter.trim();

  const allFlightsForCodeFilterQuery = useQuery({
    queryKey: ["admin-flights-all", activeAdminApiKey, statusFilter, sortBy, sortOrder],
    queryFn: () =>
      searchAllFlights({
        status: statusFilter === "all" ? undefined : statusFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    enabled: Boolean(activeAdminApiKey) && codeFilterTrimmed.length > 0,
  });

  const usersQuery = useQuery({
    queryKey: ["admin-users", activeAdminApiKey, usersPage, usersRowsPerPage],
    queryFn: () =>
      getUsersPage(
        {
          page: usersPage + 1,
          per_page: usersRowsPerPage,
        },
        activeAdminApiKey ?? undefined,
      ),
    enabled: Boolean(activeAdminApiKey),
  });

  const logsQuery = useQuery({
    queryKey: ["admin-aux-logs", activeAdminApiKey, bookingFilter, parsedLimit],
    queryFn: () =>
      getAuxLogs(
        {
          booking_id: bookingFilter || undefined,
          limit: parsedLimit,
        },
        activeAdminApiKey ?? undefined,
      ),
    enabled: Boolean(activeAdminApiKey),
    refetchInterval: 30_000,
  });

  const createFlightMutation = useMutation({
    mutationFn: (payload: Parameters<typeof createFlight>[0]) =>
      createFlight(payload, activeAdminApiKey ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-flights"] });
      setNewFlight({
        flight_code: "",
        origin_airport: "",
        destination_airport: "",
        departure_time: "",
        arrival_time: "",
        base_price: "",
      });
    },
  });

  const deleteFlightMutation = useMutation({
    mutationFn: (flightId: string) => deleteFlight(flightId, activeAdminApiKey ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-flights"] }),
  });

  const updateFlightMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateFlight>[1] }) =>
      updateFlight(id, payload, activeAdminApiKey ?? undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-flights"] });
      setEditingFlightId(null);
    },
  });

  const filteredFlights = useMemo(() => {
    const flights =
      codeFilterTrimmed.length > 0 ? (allFlightsForCodeFilterQuery.data ?? []) : (flightsQuery.data?.flights ?? []);
    if (!codeFilterTrimmed) return flights;
    const needle = codeFilterTrimmed.toLowerCase();
    return flights.filter((f) => f.flight_code.toLowerCase().includes(needle));
  }, [allFlightsForCodeFilterQuery.data, codeFilterTrimmed, flightsQuery.data?.flights]);

  const visibleFlights = useMemo(() => {
    if (codeFilterTrimmed.length === 0) return filteredFlights;
    const start = flightPage * rowsPerPage;
    return filteredFlights.slice(start, start + rowsPerPage);
  }, [codeFilterTrimmed.length, filteredFlights, flightPage, rowsPerPage]);

  const pageError =
    flightsQuery.error ??
    allFlightsForCodeFilterQuery.error ??
    usersQuery.error ??
    logsQuery.error ??
    createFlightMutation.error ??
    updateFlightMutation.error ??
    deleteFlightMutation.error;

  return (
    <Stack spacing={3}>
      <Typography variant="h5" fontWeight={700}>
        Admin Panel
      </Typography>
      <ApiErrorSnackbar error={pageError} />

      {!activeAdminApiKey ? (
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Alert severity="info">
                Enter the admin API key to unlock admin endpoints.
              </Alert>
              <TextField
                label="Admin API key"
                value={adminApiKeyInput}
                onChange={(e) => setAdminApiKeyInput(e.target.value)}
                fullWidth
              />
              <Button
                variant="contained"
                onClick={() => {
                  const key = adminApiKeyInput.trim();
                  if (!key) return;
                  setAdminApiKey(key);
                  setActiveAdminApiKey(key);
                }}
                disabled={!adminApiKeyInput.trim()}
              >
                Unlock admin panel
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : (
        <>
          <Alert severity="info">
            Admin tools (API key protected): users list, flight management, and auxiliary logs.
          </Alert>
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Button
              variant="outlined"
              onClick={() => {
                clearAdminApiKey();
                setActiveAdminApiKey(null);
              }}
            >
              Clear admin key
            </Button>
          </Stack>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Users
              </Typography>
              <Table size="small" sx={{ minWidth: 900 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>User ID</TableCell>
                    <TableCell>First Name</TableCell>
                    <TableCell>Last Name</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Updated</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(usersQuery.data?.users ?? []).map((user) => (
                    <TableRow key={user.id}>
                      <TableCell sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{user.id}</TableCell>
                      <TableCell>{user.firstname}</TableCell>
                      <TableCell>{user.lastname}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.created_at ? formatDateTimeDdMmYyyy(user.created_at) : "-"}</TableCell>
                      <TableCell>{user.updated_at ? formatDateTimeDdMmYyyy(user.updated_at) : "-"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={usersQuery.data?.pagination.total_items ?? 0}
                page={usersPage}
                rowsPerPage={usersRowsPerPage}
                onPageChange={(_event, nextPage) => setUsersPage(nextPage)}
                onRowsPerPageChange={(event) => {
                  setUsersRowsPerPage(Number(event.target.value));
                  setUsersPage(0);
                }}
                rowsPerPageOptions={[5, 10, 20, 50]}
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Create Flight
              </Typography>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4, md: 2 }}>
                  <TextField
                    fullWidth
                    label="Flight Code"
                    value={newFlight.flight_code}
                    onChange={(e) => setNewFlight((s) => ({ ...s, flight_code: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 2 }}>
                  <TextField
                    fullWidth
                    label="Origin"
                    value={newFlight.origin_airport}
                    onChange={(e) => setNewFlight((s) => ({ ...s, origin_airport: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 2 }}>
                  <TextField
                    fullWidth
                    label="Destination"
                    value={newFlight.destination_airport}
                    onChange={(e) => setNewFlight((s) => ({ ...s, destination_airport: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <TextField
                    fullWidth
                    label="Departure"
                    type="datetime-local"
                    InputLabelProps={{ shrink: true }}
                    value={newFlight.departure_time}
                    onChange={(e) => setNewFlight((s) => ({ ...s, departure_time: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <TextField
                    fullWidth
                    label="Arrival"
                    type="datetime-local"
                    InputLabelProps={{ shrink: true }}
                    value={newFlight.arrival_time}
                    onChange={(e) => setNewFlight((s) => ({ ...s, arrival_time: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 2 }}>
                  <TextField
                    fullWidth
                    label="Base Price"
                    type="number"
                    value={newFlight.base_price}
                    onChange={(e) => setNewFlight((s) => ({ ...s, base_price: e.target.value }))}
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 4, md: 2 }} display="flex" alignItems="center">
                  <Button
                    fullWidth
                    variant="contained"
                    sx={{ height: 56 }}
                    onClick={() =>
                      createFlightMutation.mutate({
                        flight_code: newFlight.flight_code.trim(),
                        origin_airport: newFlight.origin_airport.trim(),
                        destination_airport: newFlight.destination_airport.trim(),
                        departure_time: toApiDateTime(newFlight.departure_time),
                        arrival_time: toApiDateTime(newFlight.arrival_time),
                        base_price: Number(newFlight.base_price),
                      })
                    }
                    disabled={createFlightMutation.isPending}
                  >
                    Add Flight
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Manage Flights
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
                <TextField
                  label="Filter by flight code"
                  size="small"
                  value={codeFilter}
                  onChange={(e) => {
                    setCodeFilter(e.target.value);
                    setFlightPage(0);
                  }}
                  sx={{ minWidth: 200 }}
                />
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel>Status filter</InputLabel>
                  <Select
                    label="Status filter"
                    value={statusFilter}
                    onChange={(e) => {
                      setStatusFilter(
                        e.target.value as
                          | "all"
                          | "active"
                          | "inactive"
                          | "started"
                          | "en_route"
                          | "landed"
                          | "cancelled"
                          | "delayed",
                      );
                      setFlightPage(0);
                    }}
                  >
                    <MenuItem value="all">all</MenuItem>
                    <MenuItem value="active">active</MenuItem>
                    <MenuItem value="inactive">inactive</MenuItem>
                    <MenuItem value="started">started</MenuItem>
                    <MenuItem value="en_route">en_route</MenuItem>
                    <MenuItem value="landed">landed</MenuItem>
                    <MenuItem value="cancelled">cancelled</MenuItem>
                    <MenuItem value="delayed">delayed</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel>Sort by</InputLabel>
                  <Select
                    label="Sort by"
                    value={sortBy}
                    onChange={(e) => {
                      setSortBy(e.target.value as "departure_time" | "arrival_time" | "base_price");
                      setFlightPage(0);
                    }}
                  >
                    <MenuItem value="departure_time">Departure</MenuItem>
                    <MenuItem value="arrival_time">Arrival</MenuItem>
                    <MenuItem value="base_price">Price</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <InputLabel>Order</InputLabel>
                  <Select
                    label="Order"
                    value={sortOrder}
                    onChange={(e) => {
                      setSortOrder(e.target.value as "asc" | "desc");
                      setFlightPage(0);
                    }}
                  >
                    <MenuItem value="asc">Ascending</MenuItem>
                    <MenuItem value="desc">Descending</MenuItem>
                  </Select>
                </FormControl>
              </Stack>
              <Table size="small" sx={{ minWidth: 900 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Code</TableCell>
                    <TableCell>Route</TableCell>
                    <TableCell>Departure</TableCell>
                    <TableCell>Arrival</TableCell>
                    <TableCell>Price</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visibleFlights.map((f) => (
                    <TableRow key={f.id}>
                      <TableCell>{f.flight_code}</TableCell>
                      <TableCell>
                        {f.origin_airport} {"->"} {f.destination_airport}
                      </TableCell>
                      <TableCell sx={{ minWidth: 200, verticalAlign: "top" }}>
                        {editingFlightId === f.id ? (
                          <TextField
                            size="small"
                            fullWidth
                            type="datetime-local"
                            label="Departure"
                            InputLabelProps={{ shrink: true }}
                            value={editDeparture}
                            onChange={(e) => setEditDeparture(e.target.value)}
                          />
                        ) : (
                          <Typography variant="body2">{formatDateTimeDdMmYyyy(f.departure_time)}</Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ minWidth: 200, verticalAlign: "top" }}>
                        {editingFlightId === f.id ? (
                          <TextField
                            size="small"
                            fullWidth
                            type="datetime-local"
                            label="Arrival"
                            InputLabelProps={{ shrink: true }}
                            value={editArrival}
                            onChange={(e) => setEditArrival(e.target.value)}
                          />
                        ) : (
                          <Typography variant="body2">{formatDateTimeDdMmYyyy(f.arrival_time)}</Typography>
                        )}
                      </TableCell>
                      <TableCell sx={{ verticalAlign: "top" }}>
                        {editingFlightId === f.id ? (
                          <TextField
                            size="small"
                            type="number"
                            label="Price"
                            value={editPrice}
                            onChange={(e) => setEditPrice(e.target.value)}
                            sx={{ width: 100 }}
                          />
                        ) : (
                          f.base_price
                        )}
                      </TableCell>
                      <TableCell sx={{ verticalAlign: "top" }}>
                        {editingFlightId === f.id ? (
                          <FormControl size="small" sx={{ minWidth: 120 }}>
                            <InputLabel>Status</InputLabel>
                            <Select
                              label="Status"
                              value={editStatus}
                              onChange={(e) =>
                                setEditStatus(
                                  e.target.value as
                                    | "active"
                                    | "inactive"
                                    | "started"
                                    | "en_route"
                                    | "landed"
                                    | "cancelled"
                                    | "delayed",
                                )
                              }
                            >
                              <MenuItem value="active">active</MenuItem>
                              <MenuItem value="inactive">inactive</MenuItem>
                              <MenuItem value="started">started</MenuItem>
                              <MenuItem value="en_route">en_route</MenuItem>
                              <MenuItem value="landed">landed</MenuItem>
                              <MenuItem value="cancelled">cancelled</MenuItem>
                              <MenuItem value="delayed">delayed</MenuItem>
                            </Select>
                          </FormControl>
                        ) : (
                          f.status
                        )}
                      </TableCell>
                      <TableCell align="right" sx={{ verticalAlign: "top" }}>
                        <Box sx={{ display: "inline-flex", flexWrap: "wrap", gap: 1, justifyContent: "flex-end" }}>
                          {editingFlightId === f.id ? (
                            <>
                              <Button
                                size="small"
                                variant="contained"
                                onClick={() =>
                                  updateFlightMutation.mutate({
                                    id: f.id,
                                    payload: {
                                      base_price: Number(editPrice),
                                      status: editStatus,
                                      departure_time: toApiDateTime(editDeparture),
                                      arrival_time: toApiDateTime(editArrival),
                                    },
                                  })
                                }
                                disabled={updateFlightMutation.isPending}
                              >
                                Save
                              </Button>
                              <Button
                                size="small"
                                onClick={() => {
                                  setEditingFlightId(null);
                                }}
                                disabled={updateFlightMutation.isPending}
                              >
                                Cancel
                              </Button>
                            </>
                          ) : (
                            <Button
                              size="small"
                              onClick={() => {
                                setEditingFlightId(f.id);
                                setEditPrice(String(f.base_price));
                                setEditDeparture(apiDateTimeToLocalInput(f.departure_time));
                                setEditArrival(apiDateTimeToLocalInput(f.arrival_time));
                                setEditStatus(
                                  f.status as
                                    | "active"
                                    | "inactive"
                                    | "started"
                                    | "en_route"
                                    | "landed"
                                    | "cancelled"
                                    | "delayed",
                                );
                              }}
                              disabled={updateFlightMutation.isPending}
                            >
                              Update
                            </Button>
                          )}
                          <Button
                            size="small"
                            color="error"
                            onClick={() => deleteFlightMutation.mutate(f.id)}
                            disabled={deleteFlightMutation.isPending || editingFlightId === f.id}
                          >
                            Delete
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={codeFilterTrimmed.length > 0 ? filteredFlights.length : (flightsQuery.data?.pagination.total_items ?? 0)}
                page={flightPage}
                rowsPerPage={rowsPerPage}
                onPageChange={(_event, nextPage) => setFlightPage(nextPage)}
                onRowsPerPageChange={(event) => {
                  setRowsPerPage(Number(event.target.value));
                  setFlightPage(0);
                }}
                rowsPerPageOptions={[5, 10, 20]}
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Auxiliary Logs
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
                <TextField
                  label="Booking ID filter"
                  size="small"
                  value={bookingFilterInput}
                  onChange={(e) => setBookingFilterInput(e.target.value)}
                  sx={{ minWidth: 280 }}
                />
                <TextField
                  label="Limit"
                  size="small"
                  type="number"
                  value={limitInput}
                  onChange={(e) => setLimitInput(e.target.value)}
                  sx={{ width: 120 }}
                  inputProps={{ min: 1, max: 200 }}
                />
                <Button variant="contained" onClick={() => setBookingFilter(bookingFilterInput.trim())}>
                  Apply
                </Button>
                <Button variant="outlined" onClick={() => logsQuery.refetch()} disabled={logsQuery.isFetching}>
                  Refresh
                </Button>
              </Stack>
              <Table size="small" sx={{ minWidth: 980 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Received</TableCell>
                    <TableCell>Event</TableCell>
                    <TableCell>Booking</TableCell>
                    <TableCell>User Email</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Channel</TableCell>
                    <TableCell>Message</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(logsQuery.data?.notifications ?? []).map((row) => (
                    <TableRow key={row.id}>
                      <TableCell>{formatDateTimeDdMmYyyy(row.received_at)}</TableCell>
                      <TableCell>{row.event_type}</TableCell>
                      <TableCell sx={{ minWidth: 320, fontFamily: "monospace", fontSize: "0.8rem" }}>
                        <Tooltip title="Click to copy">
                          <span
                            style={{ cursor: "pointer", wordBreak: "break-all" }}
                            onClick={() => navigator.clipboard?.writeText(row.booking_id)}
                          >
                            {row.booking_id}
                          </span>
                        </Tooltip>
                      </TableCell>
                      <TableCell>{row.user_email}</TableCell>
                      <TableCell>{row.status}</TableCell>
                      <TableCell>{row.delivery_channel}</TableCell>
                      <TableCell>{row.delivery_message}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}
    </Stack>
  );
};
