import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireStaff } from "@/features/auth/RequireStaff";
import { LoginPage } from "@/features/auth/LoginPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { GenerationsPage } from "@/features/generations/GenerationsPage";
import { GenerationDetailPage } from "@/features/generations/GenerationDetailPage";
import { AgentRunsPage } from "@/features/agent-runs/AgentRunsPage";
import { AgentRunDetailPage } from "@/features/agent-runs/AgentRunDetailPage";
import { RuntimeHealthPage } from "@/features/health/RuntimeHealthPage";
import { ArtifactsPage } from "@/features/artifacts/ArtifactsPage";
import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { KnowledgeBasePage } from "@/features/knowledge/KnowledgeBasePage";

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
            path: "/projects",
            element: <ProjectsPage />,
          },
          {
            path: "/knowledge-base",
            element: <KnowledgeBasePage />,
          },
          {
            path: "/knowledge",
            element: <Navigate to="/knowledge-base" replace />,
          },
          {
            path: "/generations",
            element: <GenerationsPage />,
          },
          {
            path: "/generations/:generationId",
            element: <GenerationDetailPage />,
          },
          {
            path: "/agent-runs",
            element: <AgentRunsPage />,
          },
          {
            path: "/agent-runs/:runId",
            element: <AgentRunDetailPage />,
          },
          {
            path: "/runtime-health",
            element: <RuntimeHealthPage />,
          },
          {
            path: "/artifacts",
            element: <ArtifactsPage />,
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
