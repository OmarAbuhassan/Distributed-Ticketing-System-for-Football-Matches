import React from 'react';
import { useEffect, useState } from 'react';
import Header from '../components/Header';
import InputField from '../components/InputField';
import MatchCard from '../components/MatchCard';
import axios from 'axios';
import config from '../../config';


export default function Matches() {
  const [name, setName] = useState('');
  const [matches, setMatches] = useState([]);

  useEffect(() => {
    const fetchMatches = async () => {
      try {
        // use API_URL from config.js
        const response = await axios.get(`${config.API_URL}/matches`);
        // const response = await axios.get('http://localhost:8001/api/general/matches');
        setMatches(response.data);
      } catch (error) {
        console.error('Error fetching matches:', error);
      }
    };
    console.log('These are the matches: ', 'matches', matches);
    
    fetchMatches();
  }, []);


  return (
    <>
      <Header />
      <div className="max-w-4xl mx-auto px-4 py-8">
        <InputField label="Enter your name" value={name} onChange={(e) => setName(e.target.value)} />
        
        <div className="space-y-6">
          {matches.map((match) => (
            <MatchCard
              key={match.match_id}
              team1={match.team1_name}
              team2={match.team2_name}
              match_id={match.match_id}
              user_name={name} // Pass the name to MatchCard
            />
          ))}
        </div>
      </div>
    </>
  );
}
