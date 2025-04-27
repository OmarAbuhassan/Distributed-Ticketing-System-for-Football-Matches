// StadiumSeats.jsx
import React from 'react';
import { useState } from 'react';

const STATUS_CLASSES = {
  available: 'bg-green-500 hover:bg-green-600 cursor-pointer',
  disabled: 'bg-gray-300 cursor-not-allowed',
  reserved: 'bg-red-500 cursor-not-allowed',
  active: 'bg-blue-400 cursor-wait',
  selected: 'bg-yellow-500 ring-2 ring-yellow-300 cursor-pointer',
};

const isEnabled = (seat, category) => {
  if (category === 'Standard') {
    return seat.side === 'left' || seat.side === 'right';
  }
  if (category === 'VIP') {
    return (
      (seat.side === 'top' && (seat.layer === 4 || seat.layer === 3)) ||
      (seat.side === 'bottom' && (seat.layer === 1 || seat.layer === 2))
    );
  }
  if (category === 'Premium') {
    return (
      (seat.side === 'top' && (seat.layer === 1 || seat.layer === 2)) ||
      (seat.side === 'bottom' && (seat.layer === 3 || seat.layer === 4))
    );
  }
  return false;
};

export default function StadiumSeats({ category, onSeatSelect, seats }) {
  
  const Seat = ({ seat, style ={} }) => {


    const enabled = isEnabled(seat, category);
    const status = seat.status;
    var classes = enabled ? STATUS_CLASSES['available'] : STATUS_CLASSES[status] || STATUS_CLASSES['disabled'];

    const handleClick = () => {
      if (status !== 'available') return;
      console.log(`Selected seat: ${seat.id}`);     
      onSeatSelect(seat);
    };

    return (
      <div
        className={`w-5 h-5 rounded-full ${classes}`}
        style={style}
        title={seat.id}
        onClick={handleClick}
      />
    );
  };

  const renderStraightSide = (side) => (
    <div className="flex flex-col gap-2 items-center">
      {[1, 2, 3, 4].map(layer => (
        <div key={`${side}-layer-${layer}`} className="flex gap-2">
          {seats.filter(s => s.side === side && s.layer === layer).map(seat => <Seat key={seat.id} seat={seat}  />)}
        </div>
      ))}
    </div>
  );

  const renderCurvedSide = (side) => {
    const radius = 140;
    const angleStep = 11;
    const layers = 4;
    const seatsPerLayer = 10;
    const curveOffset = side === 'left' ? 135 : 45;
    const curveDirection = side === 'left' ? 1 : -1;
    const centerOffsetX = side === 'left' ? 200 : -200;

    return (
      <div className="relative w-72 h-72">
        {[...Array(layers)].map((_, layerIndex) => (
          <div
            key={`${side}-layer-${layerIndex}`}
            className="absolute left-1/2 top-1/2"
          >
            {[...Array(seatsPerLayer)].map((_, seatIndex) => {
              const angle = curveOffset + seatIndex * angleStep * curveDirection;
              const rad = radius + layerIndex * 25;
              const x = rad * Math.cos((angle * Math.PI) / 180);
              const y = rad * Math.sin((angle * Math.PI) / 180);
              const seat = seats.find(
                s => s.side === side && s.layer === layerIndex + 1 && s.index === seatIndex
              );
              return (
                <Seat
                  key={seat.id}
                  seat={seat}
                  style={{ 
                    position: 'absolute',
                    transform: `translate(${x + centerOffsetX}px, ${y}px)` 
                  }}
                /> 
              );
            })}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col items-center gap-8">
      {renderStraightSide('top')}
      <div className="flex items-center justify-center gap-16">
        {renderCurvedSide('left')}
        <div className="w-96 h-40 bg-gray-300 rounded-[100px] flex items-center justify-center">
          Stadium
        </div>
        {renderCurvedSide('right')}
      </div>
      {renderStraightSide('bottom')}
    </div>
  );
}
