import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import { ToastProvider } from "./components/Toast";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const CampaignList = lazy(() => import("./pages/CampaignList"));
const CampaignCreate = lazy(() => import("./pages/CampaignCreate"));
const CampaignDetail = lazy(() => import("./pages/CampaignDetail"));
const Settings = lazy(() => import("./pages/Settings"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route
                  path="/"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Dashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/campaigns"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CampaignList />
                    </Suspense>
                  }
                />
                <Route
                  path="/campaigns/new"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CampaignCreate />
                    </Suspense>
                  }
                />
                <Route
                  path="/campaigns/:id"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <CampaignDetail />
                    </Suspense>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <Suspense fallback={<PageLoader />}>
                      <Settings />
                    </Suspense>
                  }
                />
              </Route>
            </Routes>
          </BrowserRouter>
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
