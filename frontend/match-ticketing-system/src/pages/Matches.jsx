import React from 'react';
import { useState } from 'react';
import Header from '../components/Header';
import InputField from '../components/InputField';
import MatchCard from '../components/MatchCard';

const matches = [
  { title: 'Eagles vs Tigers', image: '/images/eagles-vs-tigers.jpg' },
  { title: 'Sharks vs Bears', image: '/images/sharks-vs-bears.jpg' },
  { title: 'Lions vs Wolves', image: '/images/lions-vs-wolves.jpg' },
];

export default function Matches() {
  const [name, setName] = useState('');

  return (
    <>
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <InputField label="Enter your name" value={name} onChange={(e) => setName(e.target.value)} />
        
        <div className="space-y-6">
          {matches.map((match, idx) => (
            <MatchCard key={idx} title={match.title} image={match.image} />
          ))}
        </div>
      </div>
    </>
  );
}
