import React from 'react';
import { FaTicketAlt } from 'react-icons/fa';

export default function ReservationCard({ reservation }) {
  return (
    <div className="bg-white border rounded-xl shadow-md p-5 flex items-center justify-between hover:shadow-lg transition-all duration-200">
      <div className="flex items-center gap-4">
        <FaTicketAlt className="text-2xl text-blue-900" />
        <div>
          <p className="text-lg font-semibold">Reservation #{reservation.reservation_id}</p>
          <p className="text-sm text-gray-600">User: {reservation.user_name}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div>
          <p className="text-sm text-gray-600">Match ID: {reservation.match_id}</p>
          <p className="text-sm text-gray-600">Seat ID: {reservation.seat_id}</p>
        </div>
      </div>
    </div>
  );
}