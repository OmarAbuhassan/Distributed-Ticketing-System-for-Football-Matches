import React from 'react';
export default function InputField({ label, value, onChange }) {
    return (
      <div className="relative my-6">
        <input
          type="text"
          value={value}
          onChange={onChange}
          className="peer w-full border border-gray-300 rounded-md px-3 pt-5 pb-2 focus:outline-none focus:ring-2 focus:ring-blue-600 shadow-sm"
          placeholder=" "
        />
        <label className="absolute left-3 top-2 text-sm text-gray-500 transition-all peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-400 peer-focus:top-2 peer-focus:text-sm peer-focus:text-blue-600">
          {label}
        </label>
      </div>
    );
  }