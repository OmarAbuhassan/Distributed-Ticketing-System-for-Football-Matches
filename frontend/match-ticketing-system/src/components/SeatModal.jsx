// SeatModal.jsx
import React, { useEffect, useState } from 'react';
import StadiumSeats from './StadiumSeats';
const readSeatsFromCSV = async () => {
  try {
    const response = await fetch('/seats.csv');
    const text = await response.text();
    const rows = text.split('\n').slice(1); // Skip header row
    
    const parsedSeats = rows
      .filter(row => row.trim() !== '')
      .map(row => {
        const [seat_id, seat_name, match_id, category, status] = row.split(',');
        const parsed = {
          seat_id: parseInt(seat_id),
          seat_name: seat_name.trim(),
          match_id: parseInt(match_id),
          category: category.trim(),
          status: status.trim(),
        };
        return parsed;
      });

      return parsedSeats;
  } catch (error) {
    console.error('Error reading CSV file:', error);
    return [];
  }
};

const apiSeats = await readSeatsFromCSV(); // Load seats once as a constant

const generateSeats = (category) => {
  const seats = [];
  const sides = ['top', 'bottom', 'left', 'right'];

  /* pick only the CSV rows for the current category */
  const catSeats = apiSeats.filter((s) => s.category === category);
  let stdCounter  = 0;
  let vipCounter  = 0;
  let premCounter = 0;
  let ptr         = 0;                    // index inside catSeats

  for (let layer = 1; layer <= 4; layer++) {
    for (const side of sides) {
      for (let i = 0; i < 10; i++) {

        const seat = {
          id     : `${side}-${layer}-${i}`,   // fallback id
          side,
          layer,
          index  : i,
          status : 'disabled',               // fallback
          name   : '',
        };

        /* seat name counters */
        if (category === 'Standard') seat.name = `Standard-${stdCounter++}`;
        if (category === 'VIP')      seat.name = `VIP-${vipCounter++}`;
        if (category === 'Premium')  seat.name = `Premium-${premCounter++}`;

        /* ---------------- eligibility rule (fixed) ---------------- */
        const eligible =
          /* curved edges */
          (category === 'Standard' &&
            (side === 'left' || side === 'right')) ||

          /* VIP = rows nearest pitch */
          (category === 'VIP' && (
            (side === 'top'    && (layer === 3 || layer === 4)) ||
            (side === 'bottom' && (layer === 1 || layer === 2))
          )) ||

          /* Premium = outer rows */
          (category === 'Premium' && (
            (side === 'top'    && (layer === 1 || layer === 2)) ||
            (side === 'bottom' && (layer === 3 || layer === 4))
          ));

        /* attach CSV data only if this position is eligible */
        if (eligible && ptr < catSeats.length) {
          const apiSeat = catSeats[ptr++];
          seat.id = apiSeat.seat_id;   // Make sure seat_id is not undefined
          seat.name = apiSeat.seat_name; // Also assign the name
          seat.status = apiSeat.status;          
        }
        // console.log('Generated seat:', seat); // Debug log
        seats.push(seat);
      }
    }
  }
  return seats;
};






export default function SeatModal({ onClose, category, match}) {
  const [inQueue, setInQueue] = useState(true);
  const [selectedSeat, setSelectedSeat] = useState(null);
  const seats = generateSeats(category); // Directly use the constant apiSeats

  useEffect(() => {
    const timer = setTimeout(() => setInQueue(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = () => {
    console.log("Submitting seat:");
    console.log(selectedSeat);
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
            <StadiumSeats category={category} onSeatSelect={setSelectedSeat} seats={seats} />
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
