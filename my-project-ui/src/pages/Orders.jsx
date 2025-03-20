import React, { useState, useEffect } from 'react';
import axios from 'axios';

function Orders() {
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/orders/')
      .then(response => {
        console.log("Полученные данные:", response.data);
        setOrders(response.data);
      })
      .catch(error => console.error('Ошибка загрузки заказов:', error));
  }, []);

  return (
    <div>
      <h1>Заказы</h1>
      <table border="1" cellPadding="8">
        <thead>
          <tr>
            <th>ID</th>
            <th>Номер заказа</th>
            <th>Площадка</th>
            <th>Цена с НДС</th>
            <th>Цена без НДС</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(order => (
            <tr key={order.id}>
              <td>{order.id}</td>
              <td>{order.external_no}</td>
              <td>{order.platform}</td>
              <td>{order.ati_price}</td>
              <td>{Math.floor(order.ati_price / 1.2 / 100) * 100}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default Orders;
