"""Apply best-effort resource limits, then exec a local trusted-code subprocess."""
import os
import sys
import resource

cpu = int(sys.argv[1])
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
if sys.platform.startswith('linux'):
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
os.execv(sys.argv[2], sys.argv[2:])
