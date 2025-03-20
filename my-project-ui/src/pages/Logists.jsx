import React, { useState, useEffect } from 'react';
import axios from 'axios';

function Logists() {
  const [logists, setLogists] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/logists/')
      .then(response => setLogists(response.data))
      .catch(error => console.error('Ошибка загрузки логистов:', error));
  }, []);

  return (
    <div>
      <h1>Логисты</h1>
      <table border="1" cellPadding="8">
        <thead>
          <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Contact ID</th>
          </tr>
        </thead>
        <tbody>
          {logists.map(logist => (
            <tr key={logist.id}>
              <td>{logist.id}</td>
              <td>{logist.name}</td>
              <td>{logist.contact_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Logists;
