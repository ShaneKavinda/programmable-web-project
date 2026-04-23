import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export const ProtectedRoute = ({ children }: { children: ReactNode }) => {
  const { token } = useAuth();

  if (!token) {
    return <Navigate to="/access-account" replace />;
  }
  return children;
};

