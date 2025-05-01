// SeatModal.jsx
import React, { use, useEffect, useState, useRef } from 'react';
import StadiumSeats from './StadiumSeats';
import axios from 'axios';
import config from '../../config';

const fetchSeatsFromAPI = async (matchId, category) => {
  try {
    const response = await axios.get(`${config.API_URL}/seats/${matchId}/${category}`);
    // Handle both array and object responses
    const seatsData = Array.isArray(response.data) ? response.data : [response.data];
    // Filter out any error responses
    if (response.data.error) {
      console.error('API Error:', response.data.error);
      return [];
    }
    return seatsData.map(seat => ({
      seat_id: parseInt(seat.seat_id),
      seat_name: seat.seat_name,
      match_id: parseInt(seat.match_id),
      category: seat.category,
      status: seat.status,
    }));
  } catch (error) {
    console.error('Error fetching seats:', error);
    return [];
  }
};

export default function SeatModal({ onClose, category, match, match_id, requestId, user_name }) {
  const [inQueue, setInQueue] = useState(true);
  const [showSuccess, setShowSuccess] = useState(false);
  const [isWaiting, setIsWaiting] = useState(false);
  const [selectedSeat, setSelectedSeat] = useState(null);
  const [seats, setSeats] = useState([]);
  const [waitingWs, setWaitingWs] = useState(null);
  const wsInitialized = useRef(false);
  const [isReserved, setIsReserved] = useState(false); // New state for reservation status
  
  const [reservationWs, setReservationWs] = useState(null);

  useEffect(() => {
    if (wsInitialized.current) return;
    wsInitialized.current = true;

    // Publish to queue service
    
    const waiting_service_ws = new WebSocket(config.WAITING_SERVER_URL);
    
    waiting_service_ws.onopen = () => {
      console.log('Waiting WebSocket connected');
      waiting_service_ws.send(JSON.stringify({
        action: "register".toLowerCase(),
        request_id: requestId,
        matchId: match_id,
        category: category,
        user_name: user_name,
      }));
    };

    // wait for response from waiting service
    waiting_service_ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received waiting service message:', data);
    }
    
    const publishToQueue = async () => {
      try {
        await axios.post(
          `${config.KAFKA_API_URL}?topic=match.${match_id}.${category.toLowerCase()}&request_id=${requestId}&username=${user_name}`,
          ''
        );
      } catch (error) {
        console.error('Error publishing to queue:', error);
      }
    };
    publishToQueue();
    
    waiting_service_ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      console.log('Received websocket message:', data);
      if (data.type === 'start_selection'.toLowerCase()) {
        console.log('Received start_selection message');
        const fetchedSeats = await fetchSeatsFromAPI(match_id, category);
        setSeats(generateSeats(category, fetchedSeats));
        setInQueue(false);
      } else {
        console.log('Not your request_id, ignoring message');
      }
    };

    setWaitingWs(waiting_service_ws);

    // Cleanup function moved outside of onmessage
    return () => {
      if (waiting_service_ws && waiting_service_ws.readyState === WebSocket.OPEN) {
        waiting_service_ws.close();
      }
    };
  }, [match_id, category, requestId, user_name]); // Added missing dependencies

  useEffect(() => {
    if (!inQueue) {
        const ws = new WebSocket(config.RESERVATION_SERVER_URL);          
              // Connection opened handler
      ws.onopen = () => {
        console.log('Reservation WebSocket connected');
        ws.send(JSON.stringify({
          stage: "1",
          match_id: match_id,
          category: category,
          user_name: user_name,
          request_id: requestId
        }));
      };

      // Message handler
      ws.onmessage = (event) => {
        const response = JSON.parse(event.data);
        console.log('Received reservation message:', response);

        switch(response.stage) {
          case "1":
            console.log('Reservation stage 1:', response);
            break;

          case "2":
            // Handle reservation confirmation            
            if (response.status === "success") {
              setIsWaiting(false); // Hide waiting state
              setShowSuccess(true); // Show success message
              console.log('Reservation successful:', response);              
              waitingWs.send(JSON.stringify({
                action: "finish".toLowerCase(),
                user_name: user_name,
                request_id: requestId,
                matchId: match_id,
                category: category,
                status: "confirmed"
              }));


            }
            else {
              setIsWaiting(false); // Hide waiting state
              setInQueue(false);
              setIsReserved(true) // Hide queue state
            }
            break;
          case "3":
            console.log('Received stage 3 message, updating seats...');
            // Fetch and update seats asynchronously
            (async () => {
              console.log('Fetching updated seats from API...');
              const updatedSeats = await fetchSeatsFromAPI(match_id, category);
              console.log('Received updated seats from API:', updatedSeats);
              const generatedSeats = generateSeats(category, updatedSeats);
              console.log('Generated new seats:', generatedSeats);
              setSeats(generatedSeats);
              console.log('Seats state updated');
            })();
            break;
          default:
            console.log('Unknown message stage:', response.stage);
        }
      };

      // Error handler
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      setReservationWs(ws);

      // Cleanup on unmount or when inQueue changes
    }
  }, [inQueue, match_id, category, user_name, requestId]); // Added missing dependencies

    

  const generateSeats = (category, apiSeats) => {
    const seats = [];
    const sides = ['top', 'bottom', 'left', 'right'];    
    let stdCounter  = 0;
    let vipCounter  = 0;
    let premCounter = 0;
    let ptr         = 0;                    // index inside apiSeats directly

    for (let layer = 1; layer <= 4; layer++) {
      for (const side of sides) {
        for (let i = 0; i < 10; i++) {

          const seat = {
            id     : `${side}-${layer}-${i}`, // fallback id
            side,
            layer,
            index  : i,
            status : 'disabled',  // fallback
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

          /* attach API data only if this position is eligible */
          if (eligible && ptr < apiSeats.length) {
            const apiSeat = apiSeats[ptr++];
            seat.id = apiSeat.seat_id;   // Make sure seat_id is not undefined
            seat.name = apiSeat.seat_name; // Also assign the name
            seat.status = apiSeat.status;          
          }
          seats.push(seat);
        }
      }
    }
    return seats;
  };

  const handleSubmit = () => {
    console.log("Submitting seat:");
    console.log(selectedSeat);
    if (reservationWs && reservationWs.readyState === WebSocket.OPEN) {
      reservationWs.send(JSON.stringify({
        stage: "2",
        match_id: match_id,
        category: category,
        user_name: user_name,
        seat_id: selectedSeat.id,
      }));
      setIsWaiting(true); // Show waiting state
    } else {
      console.error('WebSocket is not connected');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 shadow-lg w-[90%] max-w-6xl relative">
        <button onClick={onClose} className="absolute top-2 right-4 text-2xl">&times;</button>
        <h2 className="text-lg font-bold mb-4 text-center">{match} — Seat Reservation</h2>
        {isReserved && <div className="text-red-600 text-center mb-4">
          Seat is already reserved
        </div>}
        {inQueue ? (
          <div className="text-center space-y-4">
            <h2 className="text-xl font-semibold text-blue-800">Queue Notice</h2>
            <p className="text-gray-700">
              You have been added to the queue. Please remain on this screen while we prepare your
              seat selection interface. This ensures fair and timely access for all users.
            </p>
          </div>
        ) : isWaiting ? (
          <div className="text-center p-8">
            <div className="text-blue-600 text-xl mb-4">
              Processing your reservation...
            </div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-900 mx-auto"></div>
          </div>
        ) : showSuccess ? (
          <div className="text-center p-8">
            <div className="text-green-600 text-2xl font-bold mb-4">
              Seat Reserved Successfully!
            </div>
            <button
              onClick={onClose}
              className="mt-4 bg-blue-900 hover:bg-blue-700 text-white px-6 py-2 rounded-md transition"
            >
              Close
            </button>
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
