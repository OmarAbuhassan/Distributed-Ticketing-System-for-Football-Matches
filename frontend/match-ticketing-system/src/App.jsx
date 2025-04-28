import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Matches from './pages/Matches';
import Reservations from './pages/Reservations';
// import Home from './pages/Home'; // optional if you have a different one

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Matches />} />
        <Route path="/matches" element={<Matches />} />
        <Route path="/reservations" element={<Reservations />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
