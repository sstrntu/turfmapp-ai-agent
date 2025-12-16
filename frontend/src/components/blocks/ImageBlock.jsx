import React from "react";

export const ImageBlock = ({
  title,
  imageBase64,
  imageUrl,
  format = "png",
}) => {
  const src = imageUrl || (imageBase64 ? `data:image/${format};base64,${imageBase64}` : null);

  if (!src) {
    return null;
  }

  return (
    <div className="assistant-widget image-widget">
      <div className="widget-title">{title || "Generated Image"}</div>
      <img src={src} alt={title || "Generated image"} className="generated-image" />
    </div>
  );
};
