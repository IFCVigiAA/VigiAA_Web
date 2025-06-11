import React, { useState, useEffect } from 'react';

const WeatherComponent = () => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Coordenadas de Camboriú, SC (mesmas do seu projeto)
  const latitude = -27.014487;
  const longitude = -48.657806;
  
  // Substitua pela sua chave da API do Google Maps Platform
  const API_KEY = 'AIzaSyD7bvTiJLlDzXhVVAz59ltmZKv_thlGios';

  const fetchWeatherData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const url = `https://weather.googleapis.com/v1/currentConditions:lookup?key=${API_KEY}&location.latitude=${latitude}&location.longitude=${longitude}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Erro na API: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      setWeatherData(data);
    } catch (err) {
      setError(err.message);
      console.error('Erro ao buscar dados meteorológicos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeatherData();
  }, []);

  const formatTemperature = (temp) => {
    if (!temp) return 'N/A';
    return `${Math.round(temp.degrees)}°${temp.unit}`;
  };

  const getWeatherIcon = (iconUrl) => {
    if (!iconUrl) return null;
    return <img src={iconUrl} alt="Ícone do clima" style={{ width: '64px', height: '64px' }} />;
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Carregando dados meteorológicos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: 'red' }}>
        <p>Erro ao carregar dados: {error}</p>
        <button onClick={fetchWeatherData} style={{ marginTop: '10px', padding: '8px 16px' }}>
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!weatherData) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Nenhum dado meteorológico disponível</p>
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '20px', 
      border: '1px solid #ddd', 
      borderRadius: '8px', 
      maxWidth: '400px', 
      margin: '20px auto',
      backgroundColor: '#f9f9f9'
    }}>
      <h3 style={{ textAlign: 'center', marginBottom: '20px', color: '#00a053' }}>
        Clima em Camboriú, SC
      </h3>
      
      {weatherData.weatherCondition && (
        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          {getWeatherIcon(weatherData.weatherCondition.iconBaseUri)}
          <p style={{ margin: '10px 0', fontSize: '18px', fontWeight: 'bold' }}>
            {weatherData.weatherCondition.description?.text || 'Condição não disponível'}
          </p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
        {weatherData.temperature && (
          <div>
            <strong>Temperatura:</strong>
            <br />
            {formatTemperature(weatherData.temperature)}
          </div>
        )}

        {weatherData.feelsLikeTemperature && (
          <div>
            <strong>Sensação térmica:</strong>
            <br />
            {formatTemperature(weatherData.feelsLikeTemperature)}
          </div>
        )}

        {weatherData.humidity && (
          <div>
            <strong>Umidade:</strong>
            <br />
            {Math.round(weatherData.humidity.percent)}%
          </div>
        )}

        {weatherData.dewPoint && (
          <div>
            <strong>Ponto de orvalho:</strong>
            <br />
            {formatTemperature(weatherData.dewPoint)}
          </div>
        )}

        {weatherData.wind && weatherData.wind.speed && (
          <div>
            <strong>Vento:</strong>
            <br />
            {Math.round(weatherData.wind.speed.value)} {weatherData.wind.speed.unit}
          </div>
        )}

        {weatherData.uvIndex && (
          <div>
            <strong>Índice UV:</strong>
            <br />
            {weatherData.uvIndex.value}
          </div>
        )}
      </div>

      {weatherData.currentTime && (
        <div style={{ marginTop: '40px', textAlign: 'center', fontSize: '12px', color: '#666' }}>
          Última atualização: {new Date(weatherData.currentTime).toLocaleString('pt-BR')}
        </div>
      )}

      <button 
        onClick={fetchWeatherData}
        style={{ 
          width: '100%', 
          marginTop: '15px', 
          padding: '10px', 
          backgroundColor: '#00a053', 
          color: 'white', 
          border: 'none', 
          borderRadius: '4px',
          cursor: 'pointer'
        }}
      >
        Atualizar dados
      </button>
    </div>
  );
};

export default WeatherComponent;

