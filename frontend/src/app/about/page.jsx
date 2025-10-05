export const metadata = {
  title: "About Us",
  description: "About the HackHarvard project and team",
};

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-10 pt-20">
      <h1 className="text-3xl font-bold mb-4">About SimulWave</h1>
      <p className="text-gray-700 mb-6">
        SimulWave is an interactive web application designed to educate and inform users about tsunami risks in cities around the world. It features simulations of tsunami events paired with models determining the impact of future hypothetical tsunamis.
      </p>

      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-2">What we built</h2>
        <ul className="list-disc list-inside text-gray-700">
          <li>Three.js- and Cannon.js-based 3D simulations of tsunami events.</li>
          <li>React-based frontend with an interactive map to serve simulations.</li>
          <li>Animated marker interactions and route-based highlights</li>
        </ul>
      </section>

      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Team</h2>
        <ul className="list-disc list-inside text-gray-700">
          <li>Eric Chen - University of Illinois Urbana-Champaign - <a className="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" href="https://www.linkedin.com/in/eric-ec/">LinkedIn</a></li>
          <li>Andrew Choi - University of Illinois Urbana-Champaign - <a className="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" href="https://www.linkedin.com/in/andrew-choi-b70210305/">LinkedIn</a></li>
          <li>Avery Li - University of Virginia - <a className="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" href="https://www.linkedin.com/in/avery-li-847955260/">LinkedIn</a></li>
          <li>Victoria Zhang - University of Illinois Urbana-Champaign - <a className="underline text-blue-600 hover:text-blue-800 visited:text-purple-600" href="https://www.linkedin.com/in/victoria-zhang-975741260/">LinkedIn</a></li>
        </ul>
      </section>
    </div>
  );
}
