import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as CANNON from 'cannon-es';
import { Water } from './objects/Water';

// ===== Scene, Camera, Renderer =====
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdddddd);

const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  100000
);
camera.position.set(-1200, 300, 400);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.outputEncoding = THREE.sRGBEncoding;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
document.body.appendChild(renderer.domElement);

const cubeTextureLoader = new THREE.CubeTextureLoader();
cubeTextureLoader.setPath('public/');
const environmentMap = cubeTextureLoader.load([
  'px.png', // positive x
  'nx.png', // negative x 
  'py.png', // positive y
  'ny.png', // negative y
  'pz.png', // positive z
  'nz.png'  // negative z
]);

const poolTexture = new THREE.TextureLoader().load('./blahbalh/ocean_floor.png');

scene.background = environmentMap;
scene.environment = environmentMap;

const waterResolution = { size: 1024 };
const water = new Water({
  environmentMap,
  resolution: waterResolution.size
});
scene.add(water);



// ===== Controls =====
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.target.set(0, 100, 0);
controls.update();
controls.minPolarAngle = 0; // radians
controls.maxPolarAngle = Math.PI/2; // radians
controls.minDistance = 0;
controls.maxDistance = 1200;

// ===== Lights =====
const ambient = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambient);

const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
dirLight.position.set(300, 500, 300);
dirLight.castShadow = true;
dirLight.shadow.mapSize.set(4096, 4096);
scene.add(dirLight);

// ===== Physics World =====
const world = new CANNON.World({ gravity: new CANNON.Vec3(0, -120, 0) });
world.broadphase = new CANNON.SAPBroadphase(world);
world.solver.iterations = 15;
world.solver.tolerance = 0.001;
world.allowSleep = true;

world.defaultContactMaterial.contactEquationStiffness = 1e9;
world.defaultContactMaterial.contactEquationRelaxation = 2;
world.defaultContactMaterial.friction = 0.8;
world.defaultContactMaterial.restitution = 0.0;

const buildings = [];
const objects = [];
const buildingsToRemove = [];
const MAX_OBJECTS = 200;

const GROUND_GROUP = 1;
const BUILDING_GROUP = 2;
const SPHERE_GROUP = 4;

const groundMaterial = new CANNON.Material('ground');
const buildingMaterial = new CANNON.Material('building');
const sphereMaterial = new CANNON.Material('sphere');

world.addContactMaterial(new CANNON.ContactMaterial(groundMaterial, buildingMaterial, {
  friction: 0.9,
  restitution: 0.0,
  contactEquationStiffness: 1e9,
  contactEquationRelaxation: 2
}));

world.addContactMaterial(new CANNON.ContactMaterial(groundMaterial, sphereMaterial, {
  friction: 0.4,
  restitution: 0.3,
  contactEquationStiffness: 1e8,
  contactEquationRelaxation: 3
}));

world.addContactMaterial(new CANNON.ContactMaterial(buildingMaterial, sphereMaterial, {
  friction: 0.4,
  restitution: 0.3,
  contactEquationStiffness: 1e8,
  contactEquationRelaxation: 3
}));

// ===== Ground (visual + physics) =====
const groundMesh = new THREE.Mesh(
  new THREE.PlaneGeometry(50000, 50000),
  new THREE.MeshStandardMaterial({ color: 0x333333 })
);
groundMesh.rotation.x = -Math.PI / 2;
groundMesh.receiveShadow = true;
scene.add(groundMesh);

const groundBody = new CANNON.Body({
  mass: 0,
  material: groundMaterial,
  position: new CANNON.Vec3(0, -10, 0),
  allowSleep: false,
  collisionResponse: true
});
groundBody.addShape(new CANNON.Box(new CANNON.Vec3(25000, 1, 25000)));
groundBody.collisionFilterGroup = GROUND_GROUP;
groundBody.collisionFilterMask = SPHERE_GROUP | BUILDING_GROUP;
world.addBody(groundBody);

let city;

// ===== Activate Building (makes it dynamic) =====
function activateBuilding(body) {
  if (body.isActivated) return;
  
  body.isActivated = true;
  body.type = CANNON.Body.DYNAMIC;
  body.mass = body.storedMass;
  body.updateMassProperties();
  
  // Small initial velocity to help it start moving
  body.velocity.set(
    (Math.random() - 0.5) * 3,
    Math.random() * 1,
    (Math.random() - 0.5) * 3
  );
  
  body.linearDamping = 0.8;
  body.angularDamping = 0.8;
  body.allowSleep = true;
  body.wakeUp();
}

// ===== Damage Building =====
function damageBuilding(body, damage, impactPoint, impactVelocity) {
  body.health -= damage;
  
  // Update wireframe color based on health
  if (body.wireMaterial) {
    const ratio = Math.max(body.health / body.maxHealth, 0);
    if (ratio > 0.7) body.wireMaterial.color.set(0x00ff00);
    else if (ratio > 0.3) body.wireMaterial.color.set(0xffff00);
    else body.wireMaterial.color.set(0xff0000);
  }

  // Mark for removal if destroyed
  if (body.health <= 0) {
    buildingsToRemove.push(body);
    return;
  }

  // Activate the building (make it dynamic)
  activateBuilding(body);

  // Apply impact force
  if (impactPoint && impactVelocity) {
    const forceMagnitude = impactVelocity.length() * 2;
    const forceScale = forceMagnitude / Math.sqrt(body.storedMass);
    
    const force = new CANNON.Vec3(
      Math.min(impactVelocity.x * forceScale, 10),
      Math.min(Math.abs(impactVelocity.y) * forceScale * 0.3, 0.01),
      Math.min(impactVelocity.z * forceScale, 10)
    );
    
    // Apply at impact point for realistic rotation
    const localPoint = new CANNON.Vec3(
      impactPoint.x - body.position.x,
      impactPoint.y - body.position.y,
      impactPoint.z - body.position.z
    );
    
    body.applyImpulse(force, localPoint);
  }
}

// ===== Remove buildings =====
function processBuildingRemoval() {
  while (buildingsToRemove.length > 0) {
    const body = buildingsToRemove.pop();
    if (body.wireMesh) scene.remove(body.wireMesh);
    if (body.originalMesh && body.originalMesh.parent) {
      body.originalMesh.parent.remove(body.originalMesh);
    }
    world.removeBody(body);
    const idx = buildings.indexOf(body);
    if (idx > -1) buildings.splice(idx, 1);
  }
}

// ===== GLTF Loader & build physics proxies =====
const loader = new GLTFLoader();
loader.load('modernmodels/dubai.glb', (gltf) => {
  city = gltf.scene;
  city.updateMatrixWorld(true);
  scene.add(city);

  city.traverse((child) => {
    if (!child.isMesh) return;

    child.castShadow = true;
    child.receiveShadow = true;

    child.geometry.computeBoundingBox();
    const localBBox = child.geometry.boundingBox.clone();
    const localSize = new THREE.Vector3();
    localBBox.getSize(localSize);

    const worldScale = new THREE.Vector3();
    child.getWorldScale(worldScale);
    const worldSize = localSize.multiply(worldScale);

    const maxDim = Math.max(worldSize.x, worldSize.y, worldSize.z);
    if (maxDim < 100) return; // skip tiny or huge parts

    const center = new THREE.Vector3();
    localBBox.getCenter(center);
    child.localToWorld(center);

    const worldQuat = new THREE.Quaternion();
    child.getWorldQuaternion(worldQuat);

    const halfExtents = new CANNON.Vec3(worldSize.x / 2, worldSize.y / 2, worldSize.z / 2);
    const shape = new CANNON.Box(halfExtents);

    // approximate mass by volume (so larger buildings are heavier)
    const mass = (worldSize.x * worldSize.y * worldSize.z) * 0.01;

    const body = new CANNON.Body({
      mass: 0, // starts static / kinematic
      material: buildingMaterial,
      type: CANNON.Body.KINEMATIC,
      allowSleep: true,
      collisionResponse: true
    });

    body.storedMass = Math.max(5, Math.min(mass, 20000));
    body.position.set(center.x, center.y, center.z);
    body.quaternion.set(worldQuat.x, worldQuat.y, worldQuat.z, worldQuat.w);
    body.addShape(shape);

    body.collisionFilterGroup = BUILDING_GROUP;
    body.collisionFilterMask = SPHERE_GROUP | GROUND_GROUP;

    // debug wireframe
    const wireGeo = new THREE.BoxGeometry(worldSize.x, worldSize.y, worldSize.z);
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x00ff00,
      wireframe: true,
      transparent: true,
      opacity: 0.45,
      depthTest: true
    });
    const wireMesh = new THREE.Mesh(wireGeo, wireMat);
    wireMesh.position.copy(center);
    wireMesh.quaternion.copy(worldQuat);
    // scene.add(wireMesh);

    // store references
    body.wireMesh = wireMesh;
    body.wireMaterial = wireMat;
    body.originalMesh = child;
    body.originalParent = child.parent;
    body.localOffset = center.clone().sub(child.getWorldPosition(new THREE.Vector3()));

    // health tuned to mass so medium buildings topple with fewer hits
    body.maxHealth = Math.max(200, Math.min(3000, Math.floor(body.storedMass * 10)));
    body.health = body.maxHealth;
    body.isCrushable = true;
    body.isActivated = false;

    world.addBody(body);
    buildings.push(body);
  });

  console.log(`Loaded ${buildings.length} building bodies with wireframes`);
});

function vecLength(vector) {
  return Math.sqrt(vector[0]**2 + vector[1]**2 + vector[2]**2);
}

// ===== Launch balls =====
function launchBalls(count = 40) {
  for (let i = 0; i < count; i++) {
    const radius = Math.random() * 2 + 1.5;
    const sphereGeo = new THREE.SphereGeometry(radius, 16, 16);
    const sphereMat = new THREE.MeshStandardMaterial({ color: 0xff0000 });
    const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
    sphereMesh.castShadow = true;
    sphereMesh.receiveShadow = true;

    const x = -1800;
    const y = Math.random() * 600;
    const z = (Math.random() - 0.5) * 800;
    sphereMesh.position.set(x, y, z);
    scene.add(sphereMesh);

    const sphereBody = new CANNON.Body({
      mass: 1,
      shape: new CANNON.Sphere(radius),
      position: new CANNON.Vec3(x, y, z),
      material: sphereMaterial
    });

    sphereBody.collisionFilterGroup = SPHERE_GROUP;
    sphereBody.collisionFilterMask = GROUND_GROUP | BUILDING_GROUP;
    
    const speed = 600 + Math.random() * 80;
    sphereBody.velocity.set(speed, (Math.random() - 0.3) * 10, (Math.random() - 0.5) * 40);
    sphereBody.threeMesh = sphereMesh;

    sphereBody.addEventListener('collide', (e) => {
      const hitBody = e.body;
      if (hitBody && hitBody.isCrushable) {
        const impactSpeed = vecLength(sphereBody.velocity);
        const damage = Math.min(30, impactSpeed * 0.1);
        
        damageBuilding(
          hitBody, 
          damage, 
          sphereBody.position, 
          sphereBody.velocity.clone()
        );
      }
    });

    world.addBody(sphereBody);
    objects.push(sphereBody);
  }
}

const waveballs = [];
const lastTouched = [];
function makeBall(wave) {
  const index = waveballs.length;
  const radius = 30;
    const sphereGeo = new THREE.SphereGeometry(radius, 16, 16);
    const sphereMat = new THREE.MeshStandardMaterial({ color: 0xff0000 });
    const sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
    sphereMesh.castShadow = true;
    sphereMesh.receiveShadow = true;

    const x = wave.x;
    const y = water.position.y + wave.maxHeight/2.5;
    const z = wave.z;
    sphereMesh.position.set(x, y, z);
    //scene.add(sphereMesh);

    const sphereBody = new CANNON.Body({
      mass: 10,
      type: CANNON.Body.DYNAMIC,
      shape: new CANNON.Sphere(radius),
      position: new CANNON.Vec3(x, y, z),
      material: sphereMaterial
    });

    sphereBody.collisionFilterGroup = SPHERE_GROUP;
    sphereBody.collisionFilterMask = BUILDING_GROUP;
    
    sphereBody.threeMesh = sphereMesh;

    sphereBody.addEventListener('collide', (e) => {
      const hitBody = e.body;
      if (lastTouched[index] != hitBody) {
        lastTouched[index] = hitBody;
        if (hitBody && hitBody.isCrushable) {
          const damage = 10;
          wave.multiplier *= 0.999;
        //scene.remove(sphereMesh);
        sphereBody.radius = 0;
        //sphereBody.position.set(0, 0, 0);
          damageBuilding(
            hitBody, 
            damage, 
            sphereBody.position, 
            new THREE.Vector3(800*wave.xspeed, 0, 800*wave.zspeed)
          );
        }
      }
    });

    world.addBody(sphereBody);
    waveballs.push([wave, sphereMesh, sphereBody]);
    lastTouched.push(NaN);
    //objects.push(sphereBody);

}



document.getElementById('dropButton').addEventListener('click', () => launchBalls(60));

// ===== Animate =====
const clock = new THREE.Clock();

let elapsedTime = 0;
function animate() {
  const delta = Math.min(clock.getDelta(), 0.03);
  elapsedTime += delta;
  let newWaves = water.update(elapsedTime);
  for (let i = 0; i < newWaves.length; i++) {
    makeBall(newWaves[i]);
  }
  if (water.position.y < 50) water.position.y += .01;
  else water.position.y += .01;
  requestAnimationFrame(animate);
  
  world.step(1 / 120, delta, 3);

  // Update buildings
  for (const body of buildings) {
    if (body.wireMesh) {
      body.wireMesh.position.copy(body.position);
      body.wireMesh.quaternion.copy(body.quaternion);
    }

    if (body.originalMesh && body.originalParent) {
      const worldPos = new THREE.Vector3(body.position.x, body.position.y, body.position.z);
      const worldQuat = new THREE.Quaternion(
        body.quaternion.x, 
        body.quaternion.y, 
        body.quaternion.z, 
        body.quaternion.w
      );

      const parentWorldMatrix = new THREE.Matrix4();
      body.originalParent.updateWorldMatrix(true, false);
      parentWorldMatrix.copy(body.originalParent.matrixWorld).invert();

      const offsetWorld = body.localOffset.clone().applyQuaternion(worldQuat);
      worldPos.sub(offsetWorld);

      body.originalMesh.position.copy(worldPos).applyMatrix4(parentWorldMatrix);

      const parentWorldQuat = new THREE.Quaternion();
      body.originalParent.getWorldQuaternion(parentWorldQuat);
      body.originalMesh.quaternion.copy(worldQuat).premultiply(parentWorldQuat.invert());
      body.originalMesh.updateMatrix();
    }
  }

  // Update spheres and remove out-of-bounds ones
  for (let i = objects.length - 1; i >= 0; i--) {
    const obj = objects[i];
    if (obj.threeMesh) {
      obj.threeMesh.position.copy(obj.position);
      obj.threeMesh.quaternion.copy(obj.quaternion);
      
      if (obj.position.y < -500 || Math.abs(obj.position.x) > 3000 || Math.abs(obj.position.z) > 3000) {
        scene.remove(obj.threeMesh);
        world.removeBody(obj);
        objects.splice(i, 1);
      }
    }
  }
  for (let i = 0; i < waveballs.length; i++) {
    const wave = waveballs[i][0];
    const ball = waveballs[i][1];
    const ballBody = waveballs[i][2];
    ballBody.position.set(wave.x, wave.height/3 + water.position.y,wave.z);
    ball.position.copy(ballBody.position);
    ball.quaternion.copy(ballBody.quaternion);
    if (ball.position.y < -500 || Math.abs(ball.position.x) > 1000 || Math.abs(ball.position.z) > 1000 || wave.done()) {
        scene.remove(ball);
        ball.geometry.dispose();
        ball.material.dispose();
        world.removeBody(ball);
        waveballs.splice(i, 1);
      }
  }

  // Limit total objects
  while (objects.length > MAX_OBJECTS) {
    const obj = objects.shift();
    if (obj.threeMesh) scene.remove(obj.threeMesh);
    world.removeBody(obj);
  }

  processBuildingRemoval();
  controls.update();
  renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

animate();