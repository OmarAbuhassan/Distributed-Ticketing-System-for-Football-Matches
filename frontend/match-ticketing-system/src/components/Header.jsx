import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Header() {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Home' },
    { path: '/matches', label: 'Matches' },
    { path: '/reservations', label: 'Reservations' },
    { path: '/admin', label: 'Admin' }
  ];

  return (
    <header className="bg-blue-900 text-white shadow-lg">
      <nav className="max-w-6xl mx-auto px-4 py-4">
        <ul className="flex space-x-8">
          {navItems.map((item) => (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`hover:text-blue-200 transition-colors ${
                  location.pathname === item.path ? 'text-blue-200 font-bold' : ''
                }`}
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
