import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import LogoutIcon from "@mui/icons-material/Logout";
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  color: isActive ? "#fff" : "rgba(255,255,255,0.78)",
  textDecoration: "none",
  fontWeight: 600,
});

export const AppShell = () => {
  const { logout, user } = useAuth();

  return (
    <Box>
      <AppBar position="sticky">
        <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <FlightTakeoffIcon />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              Flight Client
            </Typography>
          </Stack>
          <Stack direction="row" spacing={3} alignItems="center">
            <NavLink to="/flights" style={navLinkStyle}>
              Flights
            </NavLink>
            <NavLink to="/bookings" style={navLinkStyle}>
              Bookings
            </NavLink>
            <NavLink to="/profile" style={navLinkStyle}>
              Profile
            </NavLink>
            <NavLink to="/access-account" style={navLinkStyle}>
              Access Account
            </NavLink>
            <NavLink to="/admin" style={navLinkStyle}>
              Admin
            </NavLink>
            {user ? (
              <>
                <Typography variant="body2">{user.firstname}</Typography>
                <Button
                  color="inherit"
                  size="small"
                  variant="outlined"
                  onClick={logout}
                  startIcon={<LogoutIcon />}
                  sx={{ borderColor: "rgba(255,255,255,0.5)", color: "#fff" }}
                >
                  Logout
                </Button>
              </>
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.9 }}>
                Guest
              </Typography>
            )}
          </Stack>
        </Toolbar>
      </AppBar>

      <Container sx={{ py: 3 }}>
        <Outlet />
      </Container>
    </Box>
  );
};

