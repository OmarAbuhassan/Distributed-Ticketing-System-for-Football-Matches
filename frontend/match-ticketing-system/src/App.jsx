import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Matches from './pages/Matches';
// import Home from './pages/Home'; // optional if you have a different one

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Matches />} /> {/* 👈 Set Matches as home */}
        <Route path="/matches" element={<Matches />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
