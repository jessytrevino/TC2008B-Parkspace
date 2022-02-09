from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import SimultaneousActivation
from mesa.datacollection import DataCollector

import numpy as np
import pandas as pd
import math
import time
import datetime

# mathplotlib lo usamos para graficar/visualizar como evoluciona el autómata celular.
#%matplotlib inline
#import matplotlib
#import matplotlib.pyplot as plt
#import matplotlib.animation as animation
#plt.rcParams["animation.html"] = "jshtml"
#matplotlib.rcParams['animation.embed_limit'] = 2**128

def get_grid(model):
    ''' funcion para ir monitoreando el grid desde el datacollector del modelo en cada step '''
    grid = np.zeros((model.grid.width, model.grid.height))
    for (contenido, x, y) in model.grid.coord_iter():
        for agent in contenido:
            if isinstance(agent, Celda):
              grid[x][y] = agent.es_cajon
            elif isinstance(agent, Carro):
              if (agent.estado == 2):
                  grid[x][y] = 3
              else:
                  grid[x][y] = 2
    return grid


class Celda(Agent):
    ''' Agente Celda '''
    def __init__(self, unique_id, model, tipo, es_cajon):
        super().__init__(unique_id, model)
        self.es_cajon = es_cajon # 0 -- calle, 1 --- cajon, 2 -- fila
        self.estado = 0 # 0 es libre y 1 es ocupado
        self.tipo = tipo # 0 -- normal, 1 -- discapacitado, 2 -- maternidad, 3 -- electrico, 4 -- carga/descarga 

    def step(self):

        vecinos = self.model.grid.get_neighbors(
            self.pos,
            moore=True,
            include_center=True
        )
        
        #for vecino in vecinos:
         #   if isinstance(vecino, Carro):
         #       if vecino.estado == 2 and vecino.pos == self.pos:
          #          self.estado = 1
          #      else:
          #          self.estado = 0

        # futuras entregas: solo recibir tipo cuando es cajon, duda si es viable: agregar si es pabellon en es_cajon.
        # imprimir tipo de agente 
        print("El cajón es tipo ")
        if self.tipo == 0:
            print("normal.")
        elif self.tipo == 1:
            print("discapacitado.")
        elif self.tipo == 2:
            print("maternidad.")
        elif self.tipo == 3:
            print("electrico.")
        elif self.tipo == 4:
            print("carga/descarga")

        # imprimir estado
        if self.estado == 0:
            print("El cajón está libre.")
        else:
            print("El cajón está ocupado.")

        #checar el estado del carro (estacionado o no estacionado en mi posicion)
        # posible informacion a mandar a unity
        print("Unity: (" + str(self.pos) + ", " + str(self.es_cajon) + ", " + str(self.tipo) + ", " + str(self.estado) + ")")

            
        

class Carro(Agent):
    def __init__(self, unique_id, model, tipo, estado, tiempo_llegar):
        ''' Agente Carro '''
        super().__init__(unique_id, model)
        self.tipo = tipo # 0 -- normal, 1 -- discapacitado, 2 -- maternidad, 3 -- electrico, 4 -- carga/descarga
        self.estado = estado # 0 - en estacionamiento, 1 - asignacion, 2 - estacionado, 3 - salio, 4 - en queue
         # todos los carros van a empezar en la misma posicion del grid
        # para siguiente entrega: cont de steps hasta activarse
        self.tiempo_llegar = tiempo_llegar
        self.celda_asignada = None 

    def step(self):

        # imprimir el tipo de agente
        print("El carro es tipo ")
        if self.tipo == 0:
            print("normal.")
        elif self.tipo == 1:
            print("discapacitado.")
        elif self.tipo == 2:
            print("maternidad.")
        elif self.tipo == 3:
            print("electrico.")
        elif self.tipo == 4:
            print("carga/descarga")

        # imprimir el estado del agente
        if self.estado == 0:
            self.current_pos = (1,0)
            print("El carro llega al estacionamiento.") # Le asignamos la posicion y cambia de estado
            posicion = self.LugarAsignado()
            if posicion is not None:
                self.estado = 1
                self.pos_final = posicion
                self.start_timer = time.time()
            print(self.start_timer - time.time())
            print(posicion)
            print(self.estado)
        elif self.estado == 1:
            print("El carro esta asignado") # Empieza a avanzar
            print(time.time() - self.start_timer)
            if (time.time() - self.start_timer) > self.tiempo_llegar:
                print("El carro ya se puede mover")
                self.model.grid.move_agent(self, self.pos_final)
                self.estado = 2
                # cuando el estado es igual a 2 empieza a avanzar en unity y se estaciona

        elif self.estado == 2:
            # Empieza a contar el tiempo del carrito estacionado, con un bool random podemos cambiar el estado del carro
            print("El carro esta estacionado")
            a = self.random.randrange(60,300) 
            self.start = time.time()
            print(a)
            if (time.time() - self.start_timer) > a:
                self.estado = 3
  
        elif self.estado == 3:
            print("El carro esta saliendo")
            self.pos_final = (self.model.width-2,0)

            if self.pos == self.pos_final:
                self.estado = 4

        elif self.estado == 4:
            print("El carro salio")

        elif self.estado == 5:
            print("El carro esta en la fila")
        
        # posible informacion a mandar a unity
        print("Unity: (" + str(self.unique_id) + ", " + str(self.pos) + ", " + str(self.tipo) + ", " + str(self.estado) + ")")
      
    # funcion para asignar lugar, se busca el cajon mas cercano
    def LugarAsignado(self):
        posicion = None
        for (contenido, x, y) in self.model.grid.coord_iter():
            for agente in contenido:
                if isinstance(agente, Celda) and agente.es_cajon == 1 and self.tipo == agente.tipo:
                    if agente.estado == 0:
                            posicion = (x,y)
                            agente.estado = 1
                            self.celda_asignada = agente.unique_id
                            return posicion
        return posicion
        

class ParkingModel(Model):
    ''' Modelo del sistema multiagente '''
    def __init__(self, width, height, cant_carros):
        self.width = width
        self.height = height
        self.cant_carros = cant_carros
        self.grid = MultiGrid(width, height, False)
        self.schedule = SimultaneousActivation(self)
        self.tiempo_max = 5
        self.tiempo = 0

        # creacion de los agentes
        # Instancias de -- Celda --
        # 20 normales 
        # 6 especiales - embarazada, electrico y handicap
        # 3 carga y descarga
        # Derecha
        for i in range(1, 21, 2):
            s = "D" + str(i)  # DERECHA - IMPAR
            print(s)
            c = Celda(s, self, 0, 1) # se crean cajones
            self.grid.place_agent(c, (i,0)) 
            self.schedule.add(c)
            s = "I" + str(i+1) # IZQUIERDA - PAR
            print(s)
            c = Celda(s, self, 0, 1) # se crean cajones
            self.grid.place_agent(c, (i+1,0)) 
            self.schedule.add(c)
        
        # 0 -- normal, 1 -- discapacitado, 2 -- maternidad, 3 -- electrico, 4 -- carga/descarga 
        c = Celda("DH", self, 1, 1) # se crean cajones
        self.grid.place_agent(c, (21,0))
        self.schedule.add(c)

        c = Celda("DP", self, 2, 1) # se crean cajones
        self.grid.place_agent(c, (23,0))
        self.schedule.add(c)

        c = Celda("DE", self, 3, 1) # se crean cajones
        self.grid.place_agent(c, (25,0))
        self.schedule.add(c)

        c = Celda("IH", self, 1, 1) # se crean cajones
        self.grid.place_agent(c, (22,0))
        self.schedule.add(c)

        c = Celda("IP", self, 2, 1) # se crean cajones
        self.grid.place_agent(c, (24,0))
        self.schedule.add(c)

        c = Celda("IE", self, 3, 1) # se crean cajones
        self.grid.place_agent(c, (26,0))
        self.schedule.add(c)

        for i in range (3):
            s = "C" + str(i) 
            print(s)
            c = Celda(s, self, 4, 1) # se crean cajones
            self.grid.place_agent(c, (27+i,0))
            self.schedule.add(c)

        tiempo_llegar = 5
        # Instancias de --Carro-- Normales
        # (self, unique_id, model, tipo, estado, tiempo_llegar)
        for i in range(self.cant_carros - 4):
            a = Carro(i, self, 0, 0, tiempo_llegar)
            self.grid.place_agent(a, (1,1))
            self.schedule.add(a)
            tiempo_llegar = tiempo_llegar + 2
        
        a = Carro(self.cant_carros - 4, self, 1, 0, tiempo_llegar)
        self.grid.place_agent(a, (1,1))
        self.schedule.add(a)

        a = Carro(self.cant_carros - 3, self, 2, 0, tiempo_llegar+2)
        self.grid.place_agent(a, (1,1))
        self.schedule.add(a)

        a = Carro(self.cant_carros - 2, self, 3, 0, tiempo_llegar+4)
        self.grid.place_agent(a, (1,1))
        self.schedule.add(a)

        a = Carro(self.cant_carros - 1, self, 4, 0, tiempo_llegar+6)
        self.grid.place_agent(a, (1,1))
        self.schedule.add(a)


        self.datacollector = DataCollector(
            model_reporters={"Grid": get_grid},
            agent_reporters={'ID Carro': lambda a: getattr(a, 'unique_id', None),
                        'Estado': lambda a: getattr(a, 'estado', None), 
                        'Celda Asignada': lambda a: getattr(a, 'celda_asignada', None),
                        'Tipo': lambda a: getattr(a, 'tipo', None)}
        )

    def status_agentes(self):
        data = list()
        for (content, x, y) in self.grid.coord_iter():
            for obj in content:
                if isinstance(obj, Carro):
                    data.append({'id_carro':obj.unique_id, 'estado': obj.estado,
                                 'celda_asignada': obj.celda_asignada, 'tipo': obj.tipo})
        
        return data


    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()

        

    