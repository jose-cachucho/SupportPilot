import logging
import os

def setup_logger(name="SupportPilot"):
    # 1. Garante que cria a pasta 'logs' na raiz de onde executas o script
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Se já tiver handlers (para não duplicar logs ao reiniciar loops), devolve logo
    if logger.hasHandlers():
        return logger

    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 2. Configuração CRÍTICA do Ficheiro
    # Garante que 'support_pilot.log' é criado
    file_handler = logging.FileHandler(os.path.join(log_dir, "support_pilot.log"), encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # print de debug para saberes se esta função correu
    print(f"[DEBUG] Logger configurado. Ficheiro: {os.path.join(log_dir, 'support_pilot.log')}")

    return logger