import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginForm from './components/LoginForm';
import SessionList from './pages/SessionList';
import SessionDetail from './pages/SessionDetail';

export default function App() {
  return (
    <BrowserRouter>
      <LoginForm />
      <Routes>
        <Route path="/sessions" element={<SessionList />} />
        <Route path="/sessions/:id" element={<SessionDetail />} />
        <Route path="*" element={<Navigate to="/sessions" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
