#!/usr/bin/env python3
"""
ROBOT DETECTOR PARA ROS2
Autor: Sebastián Aucapiña
"""

import cv2
import numpy as np
from pathlib import Path
import yaml
from ultralytics import YOLO

class RobotDetectorROS:
    def __init__(self, model_paths=None):
        """
        Inicializa detectores para ROS2
        
        Args:
            model_paths: dict con rutas a modelos
                {'yolo': '/path/yolov8n.pt', 'door': '/path/best.pt'}
        """
        # Rutas por defecto (ajustar en Raspberry Pi)
        if model_paths is None:
            model_paths = {
                'yolo': 'yolov8n.pt',
                'door': None  # Se buscará automáticamente
            }
        
        print("Inicializando RobotDetector para ROS2...")
        
        # 1. YOLO pre-entrenado
        yolo_path = model_paths['yolo']
        if Path(yolo_path).exists():
            print(f"    Cargando YOLO desde: {yolo_path}")
            self.yolo_model = YOLO(yolo_path)
        else:
            print("     YOLO no encontrado, descargando...")
            self.yolo_model = YOLO('yolov8n.pt')  # Descarga automática
        
        # 2. Modelo especializado en puertas
        door_path = model_paths.get('door')
        if door_path and Path(door_path).exists():
            print(f"    Cargando modelo de puertas: {door_path}")
            self.door_model = YOLO(door_path)
            self.has_door_model = True
        else:
            print("     No se encontró modelo de puertas")
            self.door_model = None
            self.has_door_model = False
        
        # Clases útiles (TU MAPEO ORIGINAL)
        self.useful_yolo_classes = {
            'person': 'persona',
            'chair': 'silla',
            'dining table': 'mesa',
            'backpack': 'mochila',
            'suitcase': 'mochila',
            'door': 'puerta',  # Para YOLO general
        }
        
        # Colores (TUS COLORES)
        self.colors = {
            'persona': (0, 255, 0),    # Verde
            'silla': (255, 0, 0),      # Azul
            'mesa': (0, 0, 255),       # Rojo
            'mochila': (255, 255, 0),  # Cian
            'puerta': (255, 0, 255),   # Magenta
        }
        
        # Estadísticas
        self.processing_time = 0.0
        self.frame_count = 0
        
        print("RobotDetector listo para ROS2")
    
    def detect_in_image(self, cv_image, conf_threshold=0.25):
        """
        Detecta objetos en una imagen OpenCV
        
        Returns:
            detections: Lista de dict con {'class', 'confidence', 'bbox', 'source'}
            annotated_image: Imagen con bounding boxes
            analysis: Análisis para navegación
        """
        import time
        start_time = time.time()
        
        # Detectar con YOLO general
        yolo_results = self.yolo_model(cv_image, conf=conf_threshold, verbose=False)[0]
        yolo_detections = []
        
        if yolo_results.boxes is not None:
            for box, conf, cls in zip(yolo_results.boxes.xyxy, 
                                     yolo_results.boxes.conf, 
                                      yolo_results.boxes.cls):
                class_name = self.yolo_model.names[int(cls)]
                
                if class_name in self.useful_yolo_classes:
                    mapped_name = self.useful_yolo_classes[class_name]
                    yolo_detections.append({
                        'class': mapped_name,
                        'confidence': float(conf),
                        'bbox': box.cpu().numpy().tolist(),  # [x1, y1, x2, y2]
                        'source': 'yolo'
                    })
        
        # Detectar puertas con modelo especializado
        door_detections = []
        if self.has_door_model:
            door_results = self.door_model(cv_image, conf=conf_threshold*0.8, verbose=False)[0]
            if door_results.boxes is not None:
                for box, conf in zip(door_results.boxes.xyxy, door_results.boxes.conf):
                    door_detections.append({
                        'class': 'puerta',
                        'confidence': float(conf),
                        'bbox': box.cpu().numpy().tolist(),
                        'source': 'door_model'
                    })
        
        # Combinar detecciones
        all_detections = yolo_detections + door_detections
        
        # Aplicar NMS (TU lógica)
        filtered_detections = self._apply_nms(all_detections)
        
        # Dibujar en imagen
        annotated_image = self._draw_detections(cv_image.copy(), filtered_detections)
        
        # Análisis para navegación (TU lógica)
        analysis = self._analyze_for_navigation(filtered_detections, cv_image.shape)
        
        # Calcular tiempo de procesamiento
        self.processing_time = time.time() - start_time
        self.frame_count += 1
        
        return filtered_detections, annotated_image, analysis
    
    def _apply_nms(self, detections, iou_threshold=0.5):
        """Non-Maximum Suppression (TU implementación)"""
        if len(detections) <= 1:
            return detections
        
        # Ordenar por confianza
        detections.sort(key=lambda x: x['confidence'], reverse=True)
        
        filtered = []
        while detections:
            best = detections.pop(0)
            filtered.append(best)
            
            # Filtrar superposiciones
            detections = [
                det for det in detections
                if self._iou(best['bbox'], det['bbox']) < iou_threshold
            ]
        
        return filtered
    
    def _iou(self, box1, box2):
        """Intersection over Union (TU cálculo)"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Área de intersección
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        # Áreas de las cajas
        box1_area = (x2_1 - x1_1) * (y2_1 - y1_1)
        box2_area = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # IoU
        union_area = box1_area + box2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0
    
    def _draw_detections(self, image, detections):
        """Dibuja detecciones (TU estilo)"""
        for det in detections:
            class_name = det['class']
            conf = det['confidence']
            bbox = det['bbox']
            
            if class_name in self.colors:
                x1, y1, x2, y2 = map(int, bbox)
                color = self.colors[class_name]
                
                # Dibujar caja
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                
                # Fondo para texto
                label = f"{class_name} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                
                cv2.rectangle(image, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
                cv2.putText(image, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return image
    
    def _analyze_for_navigation(self, detections, image_shape):
        """Análisis para navegación (TU lógica)"""
        height, width = image_shape[:2]
        
        analysis = {
            'targets': [],      # Puertas
            'obstacles': [],    # Sillas, mesas, mochilas
            'persons': [],      # Personas
            'free_zones': [],   # Zonas libres (simplificado)
            'warnings': []      # Advertencias
        }
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            if det['class'] == 'puerta':
                # Posición relativa
                position = "centro"
                if center_x < width * 0.33:
                    position = "izquierda"
                elif center_x > width * 0.66:
                    position = "derecha"
                
                analysis['targets'].append({
                    'class': 'puerta',
                    'position': (center_x, center_y),
                    'relative_position': position,
                    'distance_estimate': self._estimate_distance(y2 - y1, height),
                    'confidence': det['confidence']
                })
            
            elif det['class'] in ['silla', 'mesa', 'mochila']:
                analysis['obstacles'].append({
                    'class': det['class'],
                    'position': (center_x, center_y),
                    'size': (x2 - x1, y2 - y1)
                })
            
            elif det['class'] == 'persona':
                analysis['persons'].append({
                    'class': 'persona',
                    'position': (center_x, center_y),
                    'distance': self._estimate_distance(y2 - y1, height)
                })
        
        # Detectar zonas libres (simplificado)
        # Esto se puede mejorar con occupancy grid
        if not analysis['obstacles']:
            analysis['free_zones'].append({
                'description': 'centro libre',
                'position': (width/2, height/2)
            })
        
        # Advertencias
        for person in analysis['persons']:
            if person['distance'] < 2.0:  # Menos de 2 metros
                analysis['warnings'].append(f"Persona cerca: {person['distance']:.1f}m")
        
        return analysis
    
    def _estimate_distance(self, object_height, image_height):
        """Estimación simple de distancia"""
        if object_height <= 0:
            return 999.0
        # Persona de 1.7m ocupa 200px a 2m
        return (1.7 * image_height) / (object_height * 2.0)
    
    def get_statistics(self):
        """Obtiene estadísticas del detector"""
        return {
            'frame_count': self.frame_count,
            'avg_processing_time': self.processing_time,
            'fps': 1.0 / self.processing_time if self.processing_time > 0 else 0
        }
    
    def describe_scene(self, analysis):
        """
        Genera descripción en texto del entorno
        Para usar con voz
        """
        if not analysis['targets'] and not analysis['obstacles'] and not analysis['persons']:
            return "No veo objetos reconocidos en el entorno."
        
        parts = []
        
        # Puertas
        if analysis['targets']:
            doors = analysis['targets']
            if len(doors) == 1:
                door = doors[0]
                parts.append(f"Veo una puerta a la {door['relative_position']} aproximadamente a {door['distance_estimate']:.1f} metros")
            else:
                positions = [d['relative_position'] for d in doors]
                parts.append(f"Veo {len(doors)} puertas en posiciones: {', '.join(positions)}")
        
        # Personas
        if analysis['persons']:
            count = len(analysis['persons'])
            if count == 1:
                distance = analysis['persons'][0]['distance']
                parts.append(f"Hay una persona a {distance:.1f} metros")
            else:
                parts.append(f"Hay {count} personas en el área")
        
        # Obstáculos
        if analysis['obstacles']:
            # Agrupar por tipo
            from collections import Counter
            types = Counter([obj['class'] for obj in analysis['obstacles']])
            obs_desc = []
            for obj_type, count in types.items():
                if count == 1:
                    obs_desc.append(f"un {obj_type}")
                else:
                    obs_desc.append(f"{count} {obj_type}s")
            
            if obs_desc:
                parts.append(f"También veo {', '.join(obs_desc)}")
        
        # Zonas libres
        if analysis['free_zones']:
            parts.append("El camino central parece despejado")
        
        # Advertencias
        if analysis['warnings']:
            parts.append("¡Atención! " + "; ".join(analysis['warnings']))
        
        return ". ".join(parts) + "."

# Ejemplo de uso (para pruebas)
if __name__ == "__main__":
    # Prueba básica
    detector = RobotDetectorROS({
        'yolo': 'yolov8n.pt',
        'door': 'models/door_model/best.pt'  # Ajustar ruta
    })
    
    # Cargar imagen de prueba
    test_image = cv2.imread('test_image.jpg')
    if test_image is not None:
        detections, annotated, analysis = detector.detect_in_image(test_image)
        print(f"Detectados: {len(detections)} objetos")
        print(f"Análisis: {analysis}")
        
        # Mostrar
        cv2.imshow("Detección", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()