import React, { useState, useEffect } from 'react';
import axios from 'axios';

function DistributionRules() {
  const [rules, setRules] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/distribution-rules/')
      .then(response => setRules(response.data))
      .catch(error => console.error('Ошибка загрузки правил распределения:', error));
  }, []);

  return (
    <div>
      <h1>Правила распределения</h1>
      <table border="1" cellPadding="8">
        <thead>
          <tr>
            <th>ID</th>
            <th>Площадка</th>
            <th>Город загрузки</th>
            <th>Город выгрузки</th>
            <th>Логист</th>
            <th>Маржа (обычные)</th>
            <th>Маржа (аукцион)</th>
            <th>Авто-публикация (обычные)</th>
            <th>Авто-публикация (аукцион)</th>
            <th>Задержка публикации (мин)</th>
            <th>Дней оплаты</th>
            <th>Наименование груза</th>
          </tr>
        </thead>
        <tbody>
          {rules.map(rule => (
            <tr key={rule.id}>
              <td>{rule.id}</td>
              <td>{rule.platform}</td>
              <td>{rule.loading_city || '—'}</td>
              <td>{rule.unloading_city || '—'}</td>
              <td>{rule.logistician}</td>
              <td>{rule.margin_percent}</td>
              <td>{rule.auction_margin_percent}</td>
              <td>{rule.auto_publish ? 'Да' : 'Нет'}</td>
              <td>{rule.auto_publish_auction ? 'Да' : 'Нет'}</td>
              <td>{rule.publish_delay}</td>
              <td>{rule.payment_days}</td>
              <td>{rule.cargo_name}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DistributionRules;
