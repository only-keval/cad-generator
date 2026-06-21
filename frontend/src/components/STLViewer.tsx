import { Component, Suspense, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { STLLoader } from 'three-stdlib';
import * as THREE from 'three';

function useSTL(url: string): THREE.BufferGeometry | null {
  const [geom, setGeom] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    const loader = new STLLoader();
    loader.load(
      url,
      (g: THREE.BufferGeometry) => {
        g.computeVertexNormals();
        g.center();
        const box = g.boundingBox!;
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        if (maxDim > 0) {
          const scale = 5 / maxDim;
          g.scale(scale, scale, scale);
        }
        g.rotateX(-Math.PI / 2);
        setGeom(g);
      },
      undefined,
      () => setGeom(null),
    );
  }, [url]);

  return geom;
}

function Model({ url }: { url: string }) {
  const geom = useSTL(url);
  if (!geom) return null;
  return (
    <mesh geometry={geom}>
      <meshStandardMaterial color="#4a7dff" metalness={0.3} roughness={0.4} />
    </mesh>
  );
}

class ErrorBoundary extends Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="viewer-error">
          Failed to render 3D model. The STL file may be invalid.
        </div>
      );
    }
    return this.props.children;
  }
}

interface Props {
  url: string;
}

export default function STLViewer({ url }: Props) {
  return (
    <ErrorBoundary>
      <div className="stl-viewer">
        <Canvas
          camera={{ position: [8, 6, 8], fov: 50 }}
          style={{ background: '#1a1a2e' }}
        >
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 10, 5]} intensity={1} />
          <Suspense fallback={null}>
            <Model url={url} />
          </Suspense>
          <OrbitControls />
          <gridHelper args={[10, 10, '#333', '#222']} />
        </Canvas>
      </div>
    </ErrorBoundary>
  );
}
