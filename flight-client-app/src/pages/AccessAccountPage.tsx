import VpnKeyIcon from "@mui/icons-material/VpnKey";
import { Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiErrorSnackbar } from "../components/ApiErrorSnackbar";
import { useAuth } from "../context/AuthContext";
import { issueTokenByUserId } from "../services/auth";

export const AccessAccountPage = () => {
  const navigate = useNavigate();
  const { setAuth } = useAuth();
  const [userId, setUserId] = useState("");

  const mutation = useMutation({
    mutationFn: (id: string) => issueTokenByUserId(id),
    onSuccess: (data) => {
      setAuth(data.token, data.user);
      navigate("/bookings", { replace: true });
    },
  });

  return (
    <Box sx={{ minHeight: "70vh", display: "grid", placeItems: "center", px: 2 }}>
      <Paper sx={{ width: "100%", maxWidth: 520, p: 4 }}>
        <Stack spacing={2}>
          <ApiErrorSnackbar error={mutation.error} />
          <Stack direction="row" spacing={1} alignItems="center">
            <VpnKeyIcon />
            <Typography variant="h5" fontWeight={700}>
              Access Your Account
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">
            Enter your user ID to get a token and open profile, bookings, and payment pages.
            You can get this after creating a booking.
          </Typography>
          <TextField
            label="User ID"
            fullWidth
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="550e8400-e29b-41d4-a716-446655440000"
          />
          <Button
            variant="contained"
            size="large"
            onClick={() => mutation.mutate(userId.trim())}
            disabled={mutation.isPending || !userId.trim()}
          >
            {mutation.isPending ? "Accessing..." : "Access Account"}
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
};
