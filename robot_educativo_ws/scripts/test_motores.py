#!/usr/bin/env python3
"""
Script de prueba para motores DC con TB6612FNG
Conexiones según configuración:
- PWMA: GPIO13 (PIN 33)
- AIN1: GPIO19 (PIN 35)
- AIN2: GPIO26 (PIN 37)
- PWMB: GPIO12 (PIN 32)
- BIN1: GPIO16 (PIN 36)
- BIN2: GPIO20 (PIN 38)
- STBY: Pin 1 (3.3V) - No se controla por GPIO
"""

import RPi.GPIO as GPIO
import time
import sys

# Configuración de pines
# Motor A (M1) - Asumimos izquierdo
PWMA = 13
AIN1 = 19
AIN2 = 26

# Motor B (M2) - Asumimos derecho
PWMB = 12
BIN1 = 16
BIN2 = 20

# Frecuencia PWM
PWM_FREQ = 1000  # 1kHz

def setup_gpio():
    """Configura los pines GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Configurar pines como salida
    pins = [PWMA, AIN1, AIN2, PWMB, BIN1, BIN2]
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    
    # Configurar PWM
    pwm_a = GPIO.PWM(PWMA, PWM_FREQ)
    pwm_b = GPIO.PWM(PWMB, PWM_FREQ)
    pwm_a.start(0)
    pwm_b.start(0)
    
    return pwm_a, pwm_b

def motor_a_forward(pwm, speed):
    """Motor A adelante"""
    GPIO.output(AIN1, GPIO.HIGH)
    GPIO.output(AIN2, GPIO.LOW)
    pwm.ChangeDutyCycle(speed)

def motor_a_backward(pwm, speed):
    """Motor A atrás"""
    GPIO.output(AIN1, GPIO.LOW)
    GPIO.output(AIN2, GPIO.HIGH)
    pwm.ChangeDutyCycle(speed)

def motor_a_stop(pwm):
    """Motor A parar"""
    GPIO.output(AIN1, GPIO.LOW)
    GPIO.output(AIN2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)

def motor_b_forward(pwm, speed):
    """Motor B adelante"""
    GPIO.output(BIN1, GPIO.HIGH)
    GPIO.output(BIN2, GPIO.LOW)
    pwm.ChangeDutyCycle(speed)

def motor_b_backward(pwm, speed):
    """Motor B atrás"""
    GPIO.output(BIN1, GPIO.LOW)
    GPIO.output(BIN2, GPIO.HIGH)
    pwm.ChangeDutyCycle(speed)

def motor_b_stop(pwm):
    """Motor B parar"""
    GPIO.output(BIN1, GPIO.LOW)
    GPIO.output(BIN2, GPIO.LOW)
    pwm.ChangeDutyCycle(0)

def test_motores():
    """Secuencia de prueba para identificar conexiones"""
    pwm_a, pwm_b = setup_gpio()
    
    try:
        print("\n" + "="*50)
        print("PRUEBA DE MOTORES - Robot Educativo")
        print("="*50)
        print("\nSecuencia de prueba:")
        print("1. Motor A (M1) - Adelante")
        print("2. Motor A (M1) - Atrás")
        print("3. Motor B (M2) - Adelante")
        print("4. Motor B (M2) - Atrás")
        print("5. Ambos motores - Adelante")
        print("6. Ambos motores - Atrás")
        print("7. Giro izquierda (A adelante, B atrás)")
        print("8. Giro derecha (A atrás, B adelante)")
        print("\nPresiona Ctrl+C para detener\n")
        
        time.sleep(3)
        
        # 1. Motor A Adelante
        print(" Motor A (M1) - ADELANTE (50%)")
        motor_a_forward(pwm_a, 50)
        time.sleep(2)
        motor_a_stop(pwm_a)
        time.sleep(1)
        
        # 2. Motor A Atrás
        print(" Motor A (M1) - ATRÁS (50%)")
        motor_a_backward(pwm_a, 50)
        time.sleep(2)
        motor_a_stop(pwm_a)
        time.sleep(1)
        
        # 3. Motor B Adelante
        print(" Motor B (M2) - ADELANTE (50%)")
        motor_b_forward(pwm_b, 50)
        time.sleep(2)
        motor_b_stop(pwm_b)
        time.sleep(1)
        
        # 4. Motor B Atrás
        print(" Motor B (M2) - ATRÁS (50%)")
        motor_b_backward(pwm_b, 50)
        time.sleep(2)
        motor_b_stop(pwm_b)
        time.sleep(1)
        
        # 5. Ambos adelante
        print(" Ambos motores - ADELANTE (50%)")
        motor_a_forward(pwm_a, 50)
        motor_b_forward(pwm_b, 50)
        time.sleep(2)
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        time.sleep(1)
        
        # 6. Ambos atrás
        print(" Ambos motores - ATRÁS (50%)")
        motor_a_backward(pwm_a, 50)
        motor_b_backward(pwm_b, 50)
        time.sleep(2)
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        time.sleep(1)
        
        # 7. Giro izquierda
        print(" Giro IZQUIERDA (A adelante, B atrás - 40%)")
        motor_a_forward(pwm_a, 40)
        motor_b_backward(pwm_b, 40)
        time.sleep(2)
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        time.sleep(1)
        
        # 8. Giro derecha
        print(" Giro DERECHA (A atrás, B adelante - 40%)")
        motor_a_backward(pwm_a, 40)
        motor_b_forward(pwm_b, 40)
        time.sleep(2)
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        
        print("\n Prueba completada!")
        print("Observa el movimiento del robot y anota qué motor es cuál")
        
    except KeyboardInterrupt:
        print("\n\n Prueba interrumpida por el usuario")
    finally:
        # Limpiar
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()
        print("\n GPIO limpiado")

def test_velocidades():
    """Prueba adicional de diferentes velocidades"""
    pwm_a, pwm_b = setup_gpio()
    
    try:
        print("\n" + "="*50)
        print("PRUEBA DE VELOCIDADES")
        print("="*50)
        
        speeds = [20, 40, 60, 80, 100]
        
        print("\nMotor A - Variación de velocidad (adelante):")
        for speed in speeds:
            print(f"  Velocidad: {speed}%")
            motor_a_forward(pwm_a, speed)
            time.sleep(1.5)
        motor_a_stop(pwm_a)
        
        print("\nMotor B - Variación de velocidad (adelante):")
        for speed in speeds:
            print(f"  Velocidad: {speed}%")
            motor_b_forward(pwm_b, speed)
            time.sleep(1.5)
        motor_b_stop(pwm_b)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Prueba interrumpida")
    finally:
        motor_a_stop(pwm_a)
        motor_b_stop(pwm_b)
        pwm_a.stop()
        pwm_b.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    print("\n ROBOT EDUCATIVO - PRUEBA DE MOTORES")
    print("1. Prueba básica de identificación")
    print("2. Prueba de velocidades")
    
    try:
        opcion = input("\nSelecciona una opción (1/2): ")
        
        if opcion == "1":
            test_motores()
        elif opcion == "2":
            test_velocidades()
        else:
            print("Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\n Programa terminado")
        GPIO.cleanup()
