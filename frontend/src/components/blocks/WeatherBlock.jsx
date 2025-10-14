import React from "react";

const formatTemperature = (value, unit = "°F") => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${Math.round(value)}${unit}`;
};

const formatWind = (wind) => {
  if (!wind) return "--";
  if (typeof wind === "string") return wind;
  const speed = wind.speed ?? wind.value;
  const unit = wind.unit || "mph";
  const direction = wind.direction || wind.bearing || "";
  return `${Math.round(speed)}${unit}${direction ? ` ${direction}` : ""}`;
};

export const WeatherBlock = ({ data = {}, title }) => {
  const current = data.current || data.now || {};
  const forecast = Array.isArray(data.forecast) ? data.forecast : [];
  const unit = current.unit || data.unit || "°F";

  return (
    <div className="assistant-widget weather-widget">
      <div className="weather-header">
        <div>
          <div className="widget-title">{title || current.location || "Weather"}</div>
          {current.summary && <div className="weather-summary">{current.summary}</div>}
        </div>
        <div className="weather-temp">
          {formatTemperature(current.temperature ?? current.temp, unit)}
        </div>
      </div>

      <div className="weather-details">
        <div>
          <span className="detail-label">High</span>
          <span>{formatTemperature(current.high ?? current.max, unit)}</span>
        </div>
        <div>
          <span className="detail-label">Low</span>
          <span>{formatTemperature(current.low ?? current.min, unit)}</span>
        </div>
        <div>
          <span className="detail-label">Feels like</span>
          <span>{formatTemperature(current.feels_like ?? current.feelsLike, unit)}</span>
        </div>
        <div>
          <span className="detail-label">Humidity</span>
          <span>{current.humidity != null ? `${Math.round(current.humidity)}%` : "--"}</span>
        </div>
        <div>
          <span className="detail-label">Wind</span>
          <span>{formatWind(current.wind)}</span>
        </div>
      </div>

      {forecast.length > 0 && (
        <div className="weather-forecast">
          {forecast.slice(0, 5).map((day, index) => (
            <div key={`forecast-${index}`} className="forecast-day">
              <span className="forecast-day-name">{day.day || day.label || `Day ${index + 1}`}</span>
              <span className="forecast-day-summary">{day.summary || day.condition || ""}</span>
              <span className="forecast-day-temps">
                {formatTemperature(day.high, unit)} / {formatTemperature(day.low, unit)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
