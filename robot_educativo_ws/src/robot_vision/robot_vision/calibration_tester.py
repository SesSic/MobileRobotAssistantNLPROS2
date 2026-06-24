#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
import yaml

class CalibrationTester(Node):
    def __init__(self):
        super().__init__('calibration_tester')
        self.bridge = CvBridge()
        
        # Cargar calibraciÃ³n
        calib_file = '/home/sessic/robot_educativo_ws/src/robot_vision/config/usb_camera_calibration.yaml'
        self.camera_matrix, self.dist_coeffs = self.load_calibration(calib_file)
        
        # ParÃ¡metros para SLAM
        self.orb = cv2.ORB_create(nfeatures=500)  # Para detecciÃ³n de caracterÃ­sticas
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # Estado
        self.prev_frame = None
        self.prev_keypoints = None
        self.prev_descriptors = None
        
        # SuscripciÃ³n
        self.subscription = self.create_subscription(
            Image,
            '/image_raw',
            self.callback,
            10
        )
        
        self.get_logger().info(" Tester SLAM iniciado")
        self.get_logger().info("MÃ©tricas que veremos:")
        self.get_logger().info("1.  NÃºmero de caracterÃ­sticas (keypoints)")
        self.get_logger().info("2.  Calidad de matching entre frames")
        self.get_logger().info("3.  Error de reproyecciÃ³n (epipolar)")
        self.get_logger().info("4.  DistribuciÃ³n espacial de caracterÃ­sticas")
    
    def load_calibration(self, filepath):
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            K = data['camera_matrix']['data']
            camera_matrix = np.array([
                [K[0], K[1], K[2]],
                [K[3], K[4], K[5]],
                [K[6], K[7], K[8]]
            ], dtype=np.float32)
            
            D = data['distortion_coefficients']['data']
            dist_coeffs = np.array(D, dtype=np.float32)
            
            # Mostrar parÃ¡metros importantes para SLAM
            self.get_logger().info(f" ParÃ¡metros para SLAM:")
            self.get_logger().info(f"   fx={camera_matrix[0,0]:.1f}, fy={camera_matrix[1,1]:.1f}")
            self.get_logger().info(f"   cx={camera_matrix[0,2]:.1f}, cy={camera_matrix[1,2]:.1f}")
            self.get_logger().info(f"   DistorsiÃ³n: k1={dist_coeffs[0]:.3f}, k2={dist_coeffs[1]:.3f}")
            
            return camera_matrix, dist_coeffs
        except Exception as e:
            self.get_logger().error(f"Error: {e}")
            return None, None
    
    def callback(self, msg):
        try:
            # 1. Obtener imagen
            img = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 2. Corregir distorsiÃ³n
            if self.camera_matrix is not None:
                h, w = img.shape[:2]
                undistorted = cv2.undistort(img, self.camera_matrix, self.dist_coeffs)
                gray_undist = cv2.cvtColor(undistorted, cv2.COLOR_BGR2GRAY)
            else:
                undistorted = img
                gray_undist = gray
            
            # 3. Prueba 1: Detectar caracterÃ­sticas (keypoints) ORB
            kp_orig, desc_orig = self.orb.detectAndCompute(gray, None)
            kp_undist, desc_undist = self.orb.detectAndCompute(gray_undist, None)
            
            # 4. Prueba 2: Matching entre frames consecutivos
            match_quality = 0
            if self.prev_descriptors is not None and desc_undist is not None:
                matches = self.bf.match(self.prev_descriptors, desc_undist)
                matches = sorted(matches, key=lambda x: x.distance)
                match_quality = len(matches)
                
                # Calcular error de reproyecciÃ³n (simplificado)
                if len(matches) > 10:
                    reprojection_error = self.calculate_reprojection_error(
                        matches, self.prev_keypoints, kp_undist
                    )
                else:
                    reprojection_error = 999
            
            # 5. Prueba 3: DistribuciÃ³n espacial de caracterÃ­sticas
            spatial_score = self.check_spatial_distribution(kp_undist, w, h)
            
            # 6. Prueba 4: LÃ­neas rectas en patrÃ³n (si hay)
            line_straightness = self.check_line_straightness(undistorted)
            
            # 7. Crear visualizaciÃ³n
            display = self.create_visualization(
                img, undistorted, 
                kp_orig, kp_undist,
                len(kp_orig), len(kp_undist),
                match_quality,
                spatial_score,
                line_straightness
            )
            
            # 8. Actualizar estado para siguiente frame
            self.prev_frame = gray_undist
            self.prev_keypoints = kp_undist
            self.prev_descriptors = desc_undist
            
            # 9. Mostrar
            cv2.imshow('SLAM Calibration Test', display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                cv2.destroyAllWindows()
                rclpy.shutdown()
            elif key == ord('s'):
                cv2.imwrite("slam_test.jpg", display)
                self.get_logger().info("Imagen guardada")
                
        except Exception as e:
            self.get_logger().error(f"Error: {e}")
    
    def check_spatial_distribution(self, keypoints, width, height):
        """Verifica que las caracterÃ­sticas estÃ©n bien distribuidas"""
        if len(keypoints) == 0:
            return 0
        
        # Dividir imagen en 9 regiones (3x3 grid)
        grid_x = 3
        grid_y = 3
        region_w = width // grid_x
        region_h = height // grid_y
        
        region_counts = np.zeros((grid_y, grid_x))
        
        for kp in keypoints:
            x, y = int(kp.pt[0]), int(kp.pt[1])
            region_x = min(x // region_w, grid_x - 1)
            region_y = min(y // region_h, grid_y - 1)
            region_counts[region_y, region_x] += 1
        
        # Calcular score: cuÃ¡ntas regiones tienen al menos 1 caracterÃ­stica
        filled_regions = np.sum(region_counts > 0)
        return filled_regions / (grid_x * grid_y) * 100
    
    def check_line_straightness(self, image):
        """Busca lÃ­neas rectas en la imagen (para verificar calibraciÃ³n)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        
        # Detectar lÃ­neas con Hough
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=50, maxLineGap=10)
        
        if lines is None:
            return 0
        
        # Calcular "rectitud" de las lÃ­neas
        straight_lines = 0
        for line in lines[:10]:  # Solo primeras 10
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            # Calcular desviaciÃ³n de lÃ­nea recta ideal
            if length > 0:
                # Para una lÃ­nea perfecta, todos los puntos entre (x1,y1) y (x2,y2)
                # deberÃ­an estar en la imagen de bordes
                samples = 10
                xs = np.linspace(x1, x2, samples)
                ys = np.linspace(y1, y2, samples)
                
                edge_points = 0
                for x, y in zip(xs, ys):
                    if 0 <= int(x) < edges.shape[1] and 0 <= int(y) < edges.shape[0]:
                        if edges[int(y), int(x)] > 0:
                            edge_points += 1
                
                if edge_points / samples > 0.7:  # >70% de puntos en borde
                    straight_lines += 1
        
        return straight_lines
    
    def calculate_reprojection_error(self, matches, kp1, kp2):
        """Calcula error de reproyecciÃ³n (simplificado para monocular)"""
        if len(matches) < 8:
            return 999
        
        # Extraer puntos correspondientes
        pts1 = np.float32([kp1[m.queryIdx].pt for m in matches[:50]])
        pts2 = np.float32([kp2[m.trainIdx].pt for m in matches[:50]])
        
        try:
            # Calcular matriz fundamental (geometrÃ­a epipolar)
            F, mask = cv2.findFundamentalMat(pts1, pts2, cv2.FM_RANSAC, 1.0)
            
            if F is None:
                return 999
            
            # Calcular error de distancia a lÃ­nea epipolar
            lines2 = cv2.computeCorrespondEpilines(pts1.reshape(-1, 1, 2), 1, F)
            lines2 = lines2.reshape(-1, 3)
            
            errors = []
            for (x2, y2), line in zip(pts2, lines2):
                a, b, c = line
                # Distancia de punto (x2,y2) a lÃ­nea ax+by+c=0
                dist = abs(a*x2 + b*y2 + c) / np.sqrt(a*a + b*b)
                errors.append(dist)
            
            return np.mean(errors) if errors else 999
        except:
            return 999
    
    def create_visualization(self, orig, undist, kp_orig, kp_undist, 
                            count_orig, count_undist, matches, spatial, lines):
        """Crea visualizaciÃ³n completa con mÃ©tricas"""
        # Redimensionar para que quepa en pantalla
        scale = 0.6
        h, w = orig.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        
        orig_resized = cv2.resize(orig, (new_w, new_h))
        undist_resized = cv2.resize(undist, (new_w, new_h))
        
        # Dibujar keypoints
        img_kp_orig = cv2.drawKeypoints(
            orig_resized, 
            [cv2.KeyPoint(kp.pt[0]*scale, kp.pt[1]*scale, kp.size*scale) 
             for kp in kp_orig[:100]],  # Solo primeros 100
            None, color=(0, 255, 0), flags=0
        )
        
        img_kp_undist = cv2.drawKeypoints(
            undist_resized,
            [cv2.KeyPoint(kp.pt[0]*scale, kp.pt[1]*scale, kp.size*scale) 
             for kp in kp_undist[:100]],
            None, color=(0, 255, 0), flags=0
        )
        
        # Combinar imÃ¡genes
        top_row = np.hstack([img_kp_orig, img_kp_undist])
        
        # Crear panel de mÃ©tricas
        metrics_panel = np.zeros((200, new_w*2, 3), dtype=np.uint8)
        
        # AÃ±adir mÃ©tricas con colores segÃºn calidad
        font = cv2.FONT_HERSHEY_SIMPLEX
        y_pos = 30
        
        # 1. NÃºmero de caracterÃ­sticas
        color = (0, 255, 0) if count_undist > count_orig else (0, 165, 255)
        cv2.putText(metrics_panel, f"Caracteristicas: {count_orig} â {count_undist}", 
                   (10, y_pos), font, 0.6, color, 2)
        y_pos += 30
        
        # 2. Matching entre frames
        color = (0, 255, 0) if matches > 20 else (0, 165, 255) if matches > 10 else (0, 0, 255)
        cv2.putText(metrics_panel, f"Matching entre frames: {matches}", 
                   (10, y_pos), font, 0.6, color, 2)
        y_pos += 30
        
        # 3. DistribuciÃ³n espacial
        color = (0, 255, 0) if spatial > 70 else (0, 165, 255) if spatial > 50 else (0, 0, 255)
        cv2.putText(metrics_panel, f"Distribucion espacial: {spatial:.0f}%", 
                   (10, y_pos), font, 0.6, color, 2)
        y_pos += 30
        
        # 4. LÃ­neas rectas detectadas
        color = (0, 255, 0) if lines > 3 else (0, 165, 255) if lines > 1 else (0, 0, 255)
        cv2.putText(metrics_panel, f"Lineas rectas: {lines}", 
                   (10, y_pos), font, 0.6, color, 2)
        y_pos += 40
        
        # 5. EvaluaciÃ³n general para SLAM
        slam_score = (count_undist/500*25 + min(matches, 50)/50*25 + 
                     spatial/100*25 + min(lines, 10)/10*25)
        
        if slam_score > 70:
            evaluation = "â EXCELENTE para SLAM"
            color = (0, 255, 0)
        elif slam_score > 50:
            evaluation = "â ï¸  ACEPTABLE para SLAM"
            color = (0, 165, 255)
        else:
            evaluation = "â PROBLEMAS para SLAM"
            color = (0, 0, 255)
        
        cv2.putText(metrics_panel, evaluation, 
                   (10, y_pos), font, 0.7, color, 2)
        y_pos += 30
        cv2.putText(metrics_panel, f"Puntaje SLAM: {slam_score:.1f}/100", 
                   (10, y_pos), font, 0.6, (255, 255, 255), 2)
        
        # AÃ±adir leyenda
        cv2.putText(metrics_panel, "IZQ: Original (con distorsion)", 
                   (10, 180), font, 0.5, (200, 200, 200), 1)
        cv2.putText(metrics_panel, "DER: Corregida (sin distorsion)", 
                   (new_w + 10, 180), font, 0.5, (200, 200, 200), 1)
        
        # LÃ­nea divisoria
        cv2.line(metrics_panel, (new_w, 0), (new_w, 200), (100, 100, 100), 1)
        cv2.line(top_row, (new_w, 0), (new_w, new_h), (100, 100, 100), 2)
        
        # Combinar todo
        final_display = np.vstack([top_row, metrics_panel])
        
        return final_display

def main(args=None):
    rclpy.init(args=args)
    node = CalibrationTester()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("InterrupciÃ³n por teclado")
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
