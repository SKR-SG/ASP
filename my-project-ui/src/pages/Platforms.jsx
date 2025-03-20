import React, { useState, useEffect } from 'react';
import axios from 'axios';

function Platforms() {
  const [platforms, setPlatforms] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/platforms/')
      .then(response => setPlatforms(response.data))
      .catch(error => console.error('Ошибка загрузки площадок:', error));
  }, []);

  return (
    <div>
      <h1>Площадки</h1>
      <table border="1" cellPadding="8">
        <thead>
          <tr>
            <th>ID</th>
            <th>Название</th>
            <th>Включена</th>
          </tr>
        </thead>
        <tbody>
          {platforms.map(platform => (
            <tr key={platform.id}>
              <td>{platform.id}</td>
              <td>{platform.name}</td>
              <td>{platform.enabled ? 'Да' : 'Нет'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Platforms;
