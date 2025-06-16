import React, { useState, useEffect } from 'react';

const WeatherComponent = () => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const latitude = -27.014487; // Coordenadas de Camboriú
  const longitude = -48.657806; // Coordenadas de Camboriú
  const API_KEY = '762ceaf4164ae21bc3ccb5ae6c8354db';

  const fetchWeatherData = async () => {
    setLoading(true);
    setError(null);

    if (API_KEY === 'SUA_CHAVE_DE_API_AQUI' || !API_KEY) {
      setError("Por favor, substitua 'SUA_CHAVE_DE_API_AQUI' pela sua chave real da OpenWeatherMap.");
      setLoading(false);
      return;
    }

    try {
      const url = `https://api.openweathermap.org/data/2.5/weather?lat=${latitude}&lon=${longitude}&appid=${API_KEY}&units=metric&lang=pt_br`;
      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Erro na API: ${response.status} - ${response.statusText}`);
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

  const getWeatherIcon = (icon) => {
    if (!icon) return null;
    return (
      <img
        src={`https://openweathermap.org/img/wn/${icon}@2x.png`}
        alt="Ícone do clima"
        style={{ width: '64px', height: '64px' }}
      />
    );
  };

  if (loading) {
    return <div style={{ textAlign: 'center' }}>Carregando dados meteorológicos...</div>;
  }

  if (error) {
    return (
      <div style={{ textAlign: 'center', color: 'red' }}>
        <p>Erro ao carregar dados: {error}</p>
        <button onClick={fetchWeatherData}>Tentar novamente</button>
      </div>
    );
  }

  if (!weatherData) {
    return <div style={{ textAlign: 'center' }}>Nenhum dado disponível</div>;
  }

  return (
    <div
      style={{
        padding: '20px',
        border: '1px solid #ddd',
        borderRadius: '8px',
        maxWidth: '400px',
        margin: '20px auto',
        backgroundColor: '#f9f9f9',
        boxShadow: '0 4px 8px rgba(0,0,0,0.1)'
      }}
    >
      <h3 style={{ textAlign: 'center', color: '#00a053', marginBottom: '15px' }}>
        Clima em Camboriú, {weatherData.sys.country} {/* <-- ALTERAÇÃO FEITA AQUI! */}
      </h3>

      <div style={{ textAlign: 'center', marginBottom: '20px' }}>
        {getWeatherIcon(weatherData.weather[0].icon)}
        <p style={{ fontSize: '18px', fontWeight: 'bold', textTransform: 'capitalize' }}>
          {weatherData.weather[0].description}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
        <div style={{ padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
          <strong>Temperatura:</strong>
          <br />
          {Math.round(weatherData.main.temp)}°C
        </div>
        <div style={{ padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
          <strong>Sensação:</strong>
          <br />
          {Math.round(weatherData.main.feels_like)}°C
        </div>
        <div style={{ padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
          <strong>Umidade:</strong>
          <br />
          {weatherData.main.humidity}%
        </div>
        <div style={{ padding: '10px', border: '1px solid #eee', borderRadius: '5px' }}>
          <strong>Vento:</strong>
          <br />
          {Math.round(weatherData.wind.speed * 3.6)} km/h
        </div>
      </div>

      <button
        onClick={fetchWeatherData}
        style={{
          width: '100%',
          marginTop: '20px',
          padding: '12px',
          backgroundColor: '#00a053',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
          fontSize: '16px',
          fontWeight: 'bold',
          transition: 'background-color 0.3s ease'
        }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#007b40'}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#00a053'}
      >
        Atualizar dados
      </button>
    </div>
  );
};

export default WeatherComponent;