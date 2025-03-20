import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // замените на адрес вашего API

export const getOrders = () => axios.get(`${API_BASE_URL}/orders`);
export const updateOrderPrice = (orderId, newPrice) =>
  axios.patch(`${API_BASE_URL}/orders/${orderId}/price`, { new_price: newPrice });

// Добавьте другие функции для работы с правилами, логистами, площадками и т.д.
