import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireStaff } from "@/features/auth/RequireStaff";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { GenerationsPage } from "@/features/generations/GenerationsPage";
import { AgentRunsPage } from "@/features/agent-runs/AgentRunsPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <RequireStaff />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            path: "/dashboard",
            element: <DashboardPage />,
          },
          {
            path: "/generations",
            element: <GenerationsPage />,
          },
          {
            path: "/agent-runs",
            element: <AgentRunsPage />,
          },
          {
            path: "/",
            element: <Navigate to="/dashboard" replace />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/dashboard" replace />,
  },
]);
