<template>
  <div id="page_content">
    <div id="container"></div>

      <div id="info">

        <div v-if="selectedNode.name">
          <div class="info-header">{{ selectedNode.name }}</div>
            <div v-if="selectedNode.value" class="info-component">
              <div class="info-element metadata-element meta-value">{{ selectedNode.value.toLocaleString() }} €</div>
            </div>
            <div v-if="selectedNode.value" class="info-component">
              <div class="info-element">{{ selectedNode.organization.name }}</div>
            </div>
        </div>

        <div v-if="selectedNode.companies && selectedNode.companies.length > 0" class="info-component">
          <div v-for="company, index in selectedNode.companies">
            <div v-if="index <= 3">{{ company.name }}</div>
          </div>
        </div>

        <div class="tags-container">
          <div v-for="tag in selectedNode.topic_tags">
            <div>{{ tag.tag }} - {{ tag.rule }}</div>
          </div>
          <div v-for="tag in selectedNode.target_tags">
            <div>{{ tag.tag }} - {{ tag.rule }}</div>
          </div>
        </div>
        </div>
      </div>
  </div>
</template>

<script>

import axios from 'axios';
import * as Three from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { VRButton } from 'three/examples/jsm/webxr/VRButton.js';

export default {
  name: 'ThreeTest',
  components: {
  },
  data() {
    return {
      camera: null,
      scene: null,
      renderer: null,
      mesh: null,
      outlineMesh: null,
      meshes: [],
      selectedNodes: [],
      selectedNode: {},
      selectedMeshObject: null
    }
  },
  methods: {

    init() {

      const pageWidth = window.innerWidth;
      const pageHeight = window.innerHeight;

      let container = document.getElementById('container');

      container.style.width = pageWidth-400 + 'px';
      container.style.height = pageHeight + 'px';

      // Create a Three.js renderer and add it to the page
      this.renderer = new Three.WebGLRenderer({antialias: true});
      this.renderer.setSize(container.clientWidth, container.clientHeight);
      container.appendChild(this.renderer.domElement);

      // Create a Three.js scene and camera
      this.camera = new Three.PerspectiveCamera(75, container.clientWidth/container.clientHeight, 0.1, 1000);
      this.camera.position.z = 5;

      this.scene = new Three.Scene();
      this.scene.background = new Three.Color(0x000000);
      // this.scene.fog = new Three.Fog( 0x333333, 4, 8 );

      // Enable auto-rotation
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.autoRotate = true;
      this.controls.autoRotateSpeed = 1;

      // VRButton
      document.body.appendChild( VRButton.createButton( this.renderer ) );
      this.renderer.xr.enabled = true;
      this.renderer.setAnimationLoop(this.vrAnimationLoop);
    },

    vrAnimationLoop() {
      this.renderer.render( this.scene, this.camera );
    },

    animate() {
        requestAnimationFrame(this.animate);
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    },

    keyPressed(event) {
      const tag_by_number = {
        '1': 'Transportation',
        '2': 'Energy',
        '3': 'Telecom',
        '4': 'Water',
        '5': 'Demolition',
        '6': 'Renovation'
      }

      // Target tags
      if (event.key == 't') {
        this.meshes.forEach((mesh) => {

          if (mesh.metadata.target_tags.length > 0) {
            mesh.material.color.set('#FFFFFF');
          }
          else {
            mesh.material.color.setHex( 0x222222 );
          }
        });
      }
      // Companies
      else if (event.key == 'c') {
        this.meshes.forEach((mesh) => {

          if (mesh.metadata.companies.length > 0) {
            mesh.material.color.set('#FFFFFF');
          }
          else {
            mesh.material.color.setHex( 0x222222 );
          }
        });
      }
      else if (event.key in tag_by_number) {

        let tag_name = tag_by_number[event.key];

        this.meshes.forEach((mesh) => {

          let highlight = false

          for (let i=0; i < mesh.metadata.topic_tags.length; i++){
            if (mesh.metadata.topic_tags[i].tag == tag_name) {
              highlight = true
              break
            }
          }

          if (highlight) {
            mesh.material.color.set('#FFFFFF');
          }
          else {
            mesh.material.color.setHex( 0x222222 );
          }
        });
      }
      else {
        this.meshes.forEach((mesh) => {
          mesh.material.color.set(mesh.metadata.color);
        });
      }
    },

    onItemMouseDown(event) {

      event.preventDefault();
      var mouse3D = new Three.Vector3( ( event.clientX / container.clientWidth ) * 2 - 1, -( event.clientY / container.clientHeight ) * 2 + 1, 0.5);
      var raycaster =  new Three.Raycaster();
      raycaster.setFromCamera( mouse3D, this.camera );
      var intersects = raycaster.intersectObjects( this.meshes );

      if ( intersects.length > 0 ) {
        this.selectedNode = intersects[0].object.metadata
      }
    },

    sizeFromValue(value) {

      const minSize = 0.02;
      const maxSize = 0.1;
      const sizeRange = maxSize-minSize;
      const maxEuros = 100000000;

      let size = Math.min(maxEuros, value)
      size = Math.cbrt(size);
      let proportion = size/(Math.cbrt(maxEuros))
      size = (proportion*sizeRange) + minSize;

      return size

    },

    loadData() {
      this.loadCompanyData()
      this.loadOntologyData()
    },

    loadCompanyData() {

      var url = 'https://data.vxt-research.com/storage/aechack/coordinates.json'

      axios({
        method: 'get',
        url: url,
      })
      .then(response => {

        if (this.meshes.length == 0) {

          // let dataPoints = response.data.slice(0, 20);
          let dataPoints = response.data;

          // Loop through your data points and create a Three.js mesh for each one
          dataPoints.forEach((point) => {

            // Define a material to use for your scatterplot points
            let material = new Three.MeshBasicMaterial({ color: point.color });

            // Create a sphere mesh for the point
            // const geometry = new Three.SphereGeometry(0.03);
            const geometry = new Three.BoxGeometry( this.sizeFromValue(point.value), this.sizeFromValue(point.value), this.sizeFromValue(point.value) );

            this.mesh = new Three.Mesh(geometry, material);

            // Set the position of the mesh to correspond with the location of the data point
            this.mesh.position.set(point.x, point.y, point.z);

            // Add metadata
            this.mesh.metadata = point

            // Add the mesh to the scene
            this.scene.add(this.mesh);

            this.meshes.push(this.mesh);

          });

          // Add legend
          var legend_canvas = document.createElement( 'canvas' );
          legend_canvas.width = 200;
          legend_canvas.height = 300;

          var legend_context = legend_canvas.getContext('2d');

          let legend_colors = [
            '#ff0000',
            '#00ff00',
            '#0000ff',
            '#ffff00',
            '#00ffff',
            '#ff00ff',
          ]
          let legend_texts = [
            'Transportation',
            'Energy',
            'Telecom',
            'Water',
            'Demolition',
            'Renovation',
          ]
          const rowH = 28;

          for (let i=0; i < legend_colors.length; i++) {
            legend_context.beginPath();
            legend_context.rect(20, 50+(rowH*i), 40, 16);
            legend_context.fillStyle = legend_colors[i];
            legend_context.fill();
          }

          legend_context.font = "16px sans-serif";
          legend_context.fillStyle = "#eee";

          for (let i=0; i < legend_colors.length; i++) {
            legend_context.fillText(legend_texts[i], 75, 64+(rowH*i));
          }

          legend_canvas.style.position = 'absolute';
          legend_canvas.style.top =  '10px';
          legend_canvas.style.left = '10px';
          legend_canvas.style.margin = '0px';
          legend_canvas.style.padding = '0px';

          document.body.appendChild( legend_canvas );
        }
      })
      .catch(e => {
        console.log('Error receiving data', e)
      })
    },

    loadOntologyData() {

      var url = 'https://data.vxt-research.com/storage/aechack/ontology.json'

      axios({
        method: 'get',
        url: url,
      })
      .then(response => {

        // let dataPoints = response.data.slice(0, 20);
        let dataPoints = response.data;

        // Loop through your data points and create a Three.js mesh for each one
        dataPoints.forEach((point) => {

          let label_text = point.name;
          let proportion = label_text.length/16
          let canvasW = proportion*600;
          let canvasH = 60;

          const canvas = document.createElement('canvas');
          const context = canvas.getContext('2d');
          canvas.width = canvasW;
          canvas.height = canvasH;

          context.font = '44px Arial';
          context.fillStyle = '#fff';
          context.fillText(label_text, 0, 44);

          // Create a texture from the canvas element
          const texture = new Three.CanvasTexture(canvas);

          // Create a plane geometry and material with the texture
          const text_geometry = new Three.PlaneGeometry(proportion*2, 0.2);
          const text_material = new Three.MeshBasicMaterial({ side: Three.DoubleSide, transparent: true, map: texture, color: '#fff' });

          // Create a mesh object for the plane using the geometry and material
          const text_mesh = new Three.Mesh(text_geometry, text_material);

          // Set the position of the mesh and add it to the scene
          text_mesh.position.set(point.x, point.y, point.z);
          this.scene.add(text_mesh);

        });
      })
      .catch(e => {
        console.log('Error receiving data', e)
      })
    },



  },
  mounted() {
      this.init();
      this.animate();
      window.addEventListener('keydown', this.keyPressed);
      document.getElementById("container").addEventListener("mousedown", this.onItemMouseDown);
      this.loadData();
  }
}
</script>

<style scoped>
    /* //TODO give your container a size. */

#page_content {
  display: flex;
}

#container {
  width: 1200px;
  height: 800px;
}

#info {
  padding: 8px;
  width: 400px;
  text-align: left;
  font-size: 22px;
  background: black;
  color: white;
}

.info-component {
  margin-top: 32px;
  margin-bottom: 32px;
}

.info-subtitle {
  font-weight: bold;
  font-size: 26px;
}

.info-header {
  font-weight: bold;
  font-size: 32px;
  line-height: 1.0;
  margin-top: 15px;
  margin-bottom: 50px;

}
.info-description {
  font-size: 18px;
  /* line-height: 1.0; */
}
.tag-text {
  font-size: 16px;
}

.info-row {
  display: flex;
  justify-content: center;
}

.metadata-element {
  font-size: 28px;
}

.info-metadata {
  /* border: 1px dashed #ddd;
  border-radius: 5px; */

  margin-top: 20px;
  margin-bottom: 20px;
  padding: 15px;
}

.meta-value {
  color: #ffff00;
}

.tags-container {
  margin-top: 100px;
  color: #8ff;
  /* font-variant: small-caps; */
  text-transform: uppercase
}

</style>
