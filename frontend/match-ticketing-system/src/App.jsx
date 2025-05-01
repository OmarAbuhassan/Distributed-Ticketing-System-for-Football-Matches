import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
// import Home from './pages/Home';
import Matches from './pages/Matches';
import Reservations from './pages/Reservations';
import Admin from './pages/Admin';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Matches />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </Router>
  );
}

export default App;
