import React, { useState } from 'react';
import { FaTicketAlt } from 'react-icons/fa';
import { BsFillCheckCircleFill } from 'react-icons/bs';
import SeatModal from './SeatModal'; // 💡 Make sure path is correct
import axios from 'axios';

export default function MatchCard({team1, team2, match_id, user_name }) {
  const [ticketType, setTicketType] = useState('Standard');
  const [showModal, setShowModal] = useState(false);
  const [requestId, setRequestId] = useState(null); // State to hold request ID

  const handleReserveClick = async () => {
    try {
      const response = await axios.post('http://localhost:8001/api/general/requests', {
        match_id: match_id,
        user_name:  user_name, 
        latest_status: 'submitted',
        timestamp: new Date().toISOString(),
      });
      setRequestId(response.data.request_id); // Store the request ID
      setShowModal(true);

      
    } catch (error) {
      console.error('Error making reservation:', error);
    }
  };

  return (
    <>
      <div className="bg-white border rounded-xl shadow-md p-5 flex items-center justify-between hover:shadow-lg transition-all duration-200">
        <div className="flex items-center gap-4">
          {/* <img src={image} alt={title} className="w-16 h-16 rounded-full object-cover border" /> */}
          <div>
            <p className="text-lg font-semibold">{team1} VS {team2}</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <FaTicketAlt className="absolute left-2 top-2.5 text-gray-400" />
            <select
              className="pl-8 pr-4 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={ticketType}
              onChange={(e) => setTicketType(e.target.value)}
            >
              <option value="Standard">Standard</option>
              <option value="VIP">VIP</option>
              <option value="Premium">Premium</option>
            </select>
          </div>

          <button
            className="flex items-center gap-1 bg-blue-900 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition"
            onClick={handleReserveClick}
          >
            <BsFillCheckCircleFill className="text-white" />
            Reserve
          </button>
        </div>
      </div>

      {/* 💥 Show SeatModal if triggered */}
      {showModal && (
        <SeatModal
          match={team1 + ' VS ' + team2}
          match_id={match_id}
          category={ticketType}
          onClose={() => setShowModal(false)}
          requestId={requestId} // Pass the request ID to SeatModal
          user_name={user_name} // Pass the user name to SeatModal
        />
      )}
    </>
  );
}