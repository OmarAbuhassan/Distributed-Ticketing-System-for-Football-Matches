import React from 'react';
import { Link } from 'react-router-dom';

export default function Header() {
  return (
    <header className="bg-blue-900 text-white px-6 py-4 flex justify-between items-center shadow-md">
      <div className="text-xl font-bold tracking-wide">📋 MatchMaste</div>
      <nav className="space-x-6 text-sm font-medium">
        <Link to="/" className="hover:underline">Home</Link>
        <Link to="/matches" className="hover:underline">Matches</Link>
        <Link to="/contact" className="hover:underline">Contact</Link>
        <Link to="/reservations" className="hover:underline">Reservations</Link>
      </nav>
    </header>
  );
}
