/** @type {import('next').NextConfig} */
const nextConfig = {
  // output standalone: empaqueta solo las dependencias necesarias para producción.
  // Necesario para el Dockerfile multi-stage (node server.js en lugar de next start).
  output: "standalone",

  // En Cloud Run, NEXT_PUBLIC_API_URL se hornea en build-time vía --build-arg.
  // En desarrollo local usa http://localhost:8000 (default en page.tsx).
};

export default nextConfig;
