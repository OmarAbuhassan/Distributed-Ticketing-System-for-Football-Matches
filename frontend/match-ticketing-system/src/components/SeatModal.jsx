// SeatModal.jsx
import React, { useEffect, useState } from 'react';
import StadiumSeats from './StadiumSeats';

export default function SeatModal({ onClose, category, match }) {
  const [inQueue, setInQueue] = useState(true);
  const [selectedSeat, setSelectedSeat] = useState(null);

  useEffect(() => {
    const timer = setTimeout(() => setInQueue(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = () => {
    console.log("Submitting seat:");
    
    if (selectedSeat) {
      console.log("Submitting seat:", selectedSeat);
      // add backend logic here
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 shadow-lg w-[90%] max-w-6xl relative">
        <button onClick={onClose} className="absolute top-2 right-4 text-2xl">&times;</button>
        <h2 className="text-lg font-bold mb-4 text-center">{match} — Seat Reservation</h2>
        {inQueue ? (
          <div className="text-center space-y-4">
            <h2 className="text-xl font-semibold text-blue-800">Queue Notice</h2>
            <p className="text-gray-700">
              You have been added to the queue. Please remain on this screen while we prepare your
              seat selection interface. This ensures fair and timely access for all users.
            </p>
          </div>
        ) : (
          <>
            <StadiumSeats category={category} onSeatSelect={setSelectedSeat} />
            <div className="mt-6 flex justify-end">
              <button
                disabled={!selectedSeat}
                onClick={handleSubmit}
                className={`flex items-center gap-1 px-4 py-2 rounded-md transition ${
                  selectedSeat
                    ? 'bg-blue-900 hover:bg-blue-700 text-white'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                Confirm Reservation
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
