import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import MainLayout from './components/layout/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ServerList from './pages/servers/ServerList';
import ServerDetail from './pages/servers/ServerDetail';
import UserList from './pages/users/UserList';
import MonitoringDashboard from './pages/monitoring/MonitoringDashboard';
import ClusterManagement from './pages/clusters/ClusterManagement';
import DeviceDiscovery from './pages/discovery/DeviceDiscovery';
import PrivateRoute from './components/auth/PrivateRoute';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="servers" element={<ServerList />} />
            <Route path="servers/:id" element={<ServerDetail />} />
            <Route path="clusters" element={<ClusterManagement />} />
            <Route path="discovery" element={<DeviceDiscovery />} />
            <Route path="users" element={<UserList />} />
            <Route path="monitoring" element={<MonitoringDashboard />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;