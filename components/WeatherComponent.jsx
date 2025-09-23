import React, { useState, useEffect } from 'react';

const WeatherComponent = () => {
  const [weatherData, setWeatherData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const latitude = -27.014487;
  const longitude = -48.657806;
  const API_KEY = '762ceaf4164ae21bc3ccb5ae6c8354db';

  const fetchWeatherData = async () => {
    setLoading(true);
    setError(null);

    if (!API_KEY || API_KEY === 'SUA_CHAVE_DE_API_AQUI') {
      setError("API Key inválida.");
      setLoading(false);
      return;
    }

    try {
      const url = `https://api.openweathermap.org/data/2.5/weather?lat=${latitude}&lon=${longitude}&appid=${API_KEY}&units=metric&lang=pt_br`;
      const response = await fetch(url);

      if (!response.ok) throw new Error(`Erro: ${response.status}`);

      const data = await response.json();
      setWeatherData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeatherData();
  }, []);

  const getWeatherIcon = (icon) =>
    icon ? (
      <img
        src={`https://openweathermap.org/img/wn/${icon}@2x.png`}
        alt="Ícone do clima"
        style={{ width: '50px', height: '50px' }}
      />
    ) : null;

  if (loading) return <p style={{ textAlign: 'center' }}>Carregando...</p>;
  if (error)
    return (
      <div style={{ textAlign: 'center', color: 'red' }}>
        <p>Erro: {error}</p>
        <button onClick={fetchWeatherData}>Tentar novamente</button>
      </div>
    );
  if (!weatherData) return <p style={{ textAlign: 'center' }}>Sem dados</p>;

  return (
    <div
      style={{
        padding: '15px',
        borderRadius: '6px',
        maxWidth: '300px',
        margin: '15px auto',
        fontSize: '14px',
        textAlign: 'center'
      }}
    >
      <h4 style={{ marginBottom: '10px', color: '#007b40' }}>
        Camboriú, {weatherData.sys.country}
      </h4>

      {getWeatherIcon(weatherData.weather[0].icon)}
      <p style={{ margin: '8px 0', fontWeight: '500', textTransform: 'capitalize' }}>
        {weatherData.weather[0].description}
      </p>

      <ul style={{ listStyle: 'none', padding: 0, margin: '10px 0', textAlign: 'left' }}>
        <li><strong>Temp:</strong> {Math.round(weatherData.main.temp)}°C</li>
        <li><strong>Sensação:</strong> {Math.round(weatherData.main.feels_like)}°C</li>
        <li><strong>Umidade:</strong> {weatherData.main.humidity}%</li>
        <li><strong>Vento:</strong> {Math.round(weatherData.wind.speed * 3.6)} km/h</li>
      </ul>

      <button
        onClick={fetchWeatherData}
        style={{
          width: '100%',
          marginTop: '10px',
          padding: '8px',
          backgroundColor: '#007b40',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px'
        }}
      >
        Atualizar
      </button>
    </div>
  );
};

export default WeatherComponent;
