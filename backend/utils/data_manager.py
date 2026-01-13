# backend/utils/data_manager.py

import csv
import os
from typing import List, Dict, Any, Tuple, Optional

class DataManager:
    """
    Clase centralizada para Importar y Exportar CSVs de forma segura.
    Valida cabeceras para evitar mezclar archivos de diferentes secciones.
    """

    @staticmethod
    def export_csv(filepath: str, headers: List[str], data: List[List[Any]]) -> bool:
        """
        Exporta datos a CSV.
        :param filepath: Ruta de destino.
        :param headers: Lista de nombres de columnas.
        :param data: Lista de filas (donde cada fila es una lista de valores).
        """
        try:
            # Asegurar directorio si no existe
            os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"[DataManager] Error exportando: {e}")
            return False

    @staticmethod
    def import_csv(filepath: str, required_columns: List[str]) -> Tuple[Optional[List[Dict[str, str]]], Optional[str]]:
        """
        Importa y valida un CSV.
        :param filepath: Ruta del archivo.
        :param required_columns: Lista de columnas OBLIGATORIAS (en minúsculas) para aceptar el archivo.
        :return: (Lista de Diccionarios o None, Mensaje de Error o None)
        """
        if not os.path.exists(filepath):
            return None, "El archivo no existe."

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # 1. Validación de Cabeceras
                # Obtenemos las cabeceras del archivo y las normalizamos a minúsculas
                file_headers = [h.lower().strip() for h in (reader.fieldnames or [])]
                
                # Verificamos que TODAS las columnas requeridas estén presentes
                missing = [col for col in required_columns if col.lower() not in file_headers]
                
                if missing:
                    return None, f"Archivo inválido. Faltan las columnas: {', '.join(missing)}"

                # 2. Lectura de Datos
                # Convertimos todo a una lista de diccionarios limpios
                data_list = []
                for row in reader:
                    # Normalizamos las llaves del diccionario a minúsculas para facilitar la lectura posterior
                    clean_row = {k.lower().strip(): v for k, v in row.items() if k}
                    data_list.append(clean_row)
                
                return data_list, None

        except Exception as e:
            return None, f"Error de lectura: {str(e)}"