import flowbite from "flowbite/plugin";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}", "./node_modules/flowbite/**/*.js"],
  theme: {
    extend: {
      backgroundImage: {
        bg1: "url('./assets/bg.png')",
        regbg: "url('./assets/aa.png')",
      },
      backgroundSize: { stretch: "100% 100%" },
    },
  },
  darkMode: "class",
  plugins: [flowbite],
};
