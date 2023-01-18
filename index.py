
import logging
from logging import config

config.fileConfig('log.conf')
logger = logging.getLogger('root')

logger.info('info message')
logger.warning('warn message')
logger.error('error message')
logger.critical('critical message')