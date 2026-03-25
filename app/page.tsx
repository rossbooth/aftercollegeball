import Hero from '@/components/Hero';
import SankeyDiagram from '@/components/SankeyDiagram';

export default function Home() {
  return (
    <main className="flex-1">
      <Hero />
      <SankeyDiagram />
    </main>
  );
}
