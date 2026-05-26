/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../getsync/web/templates/**/*.html",
    "../getsync/web/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0f766e",
          dark: "#0d5c56",
          light: "#14b8a6",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
