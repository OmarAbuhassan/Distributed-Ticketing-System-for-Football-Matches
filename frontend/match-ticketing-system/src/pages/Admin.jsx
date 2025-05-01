import React, { useState } from 'react';
import Header from '../components/Header';
import axios from 'axios';
import config from '../../config';

export default function Admin() {
  const [reservationId, setReservationId] = useState('');
  const [message, setMessage] = useState({ text: '', type: '' });
  const [loading, setLoading] = useState(false);

  const handleCheckIn = async () => {
    try {
        setLoading(true);
        console.log('Before check-in request');
        const response = await axios.post(`${config.API_URL}/check_in`, {
            reservation_id: reservationId,
            status: 'checked_in',
            timestamp: new Date().toISOString()
        });
        console.log(response.data);
        if (response.data.status === 'success') {
            setMessage({ text: response.data.message, type: 'success' });
        } else {
            setMessage({ text: response.data.message, type: 'error' });
        }
        setReservationId('');
    } catch (error) {
      setMessage({ text: error.response?.data?.message || 'Error during check-in', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleCheckOut = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${config.API_URL}/check_out`, {
        reservation_id: reservationId,
        status: 'checked_out',
        timestamp: new Date().toISOString()
      });
      setMessage({ text: 'Check-out successful!', type: 'success' });
      setReservationId('');
    } catch (error) {
      setMessage({ text: error.response?.data?.message || 'Error during check-out', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header />
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-md mx-auto bg-white rounded-xl shadow-md p-8">
          <h1 className="text-3xl font-bold text-blue-900 mb-8">Stadium Access Control</h1>
          
          <div className="space-y-6">
            <div>
              <label htmlFor="reservationId" className="block text-sm font-medium text-gray-700 mb-2">
                Reservation ID
              </label>
              <input
                type="text"
                id="reservationId"
                value={reservationId}
                onChange={(e) => setReservationId(e.target.value)}
                className="w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter reservation ID"
              />
            </div>

            {message.text && (
              <div className={`p-4 rounded-md ${
                message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {message.text}
              </div>
            )}

            <div className="flex gap-4">
              <button
                onClick={handleCheckIn}
                disabled={loading || !reservationId}
                className={`flex-1 py-2 px-4 rounded-md ${
                  loading || !reservationId
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-900 hover:bg-blue-700 text-white'
                }`}
              >
                Check In
              </button>
              <button
                onClick={handleCheckOut}
                disabled={loading || !reservationId}
                className={`flex-1 py-2 px-4 rounded-md ${
                  loading || !reservationId
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-blue-900 hover:bg-blue-700 text-white'
                }`}
              >
                Check Out
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}