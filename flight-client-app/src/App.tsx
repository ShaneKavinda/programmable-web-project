import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AccessAccountPage } from "./pages/AccessAccountPage";
import { BookingWizardPage } from "./pages/BookingWizardPage";
import { BookingsPage } from "./pages/BookingsPage";
import { FlightsPage } from "./pages/FlightsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PaymentPage } from "./pages/PaymentPage";
import { ProfilePage } from "./pages/ProfilePage";
import { AdminPanelPage } from "./pages/AdminPanelPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Navigate to="/flights" replace />} />
        <Route path="flights" element={<FlightsPage />} />
        <Route path="book/new" element={<BookingWizardPage />} />
        <Route
          path="bookings"
          element={
            <ProtectedRoute>
              <BookingsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="bookings/:bookingId/pay"
          element={
            <ProtectedRoute>
              <PaymentPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />
        <Route path="access-account" element={<AccessAccountPage />} />
        <Route path="admin" element={<AdminPanelPage />} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}

export default App;
