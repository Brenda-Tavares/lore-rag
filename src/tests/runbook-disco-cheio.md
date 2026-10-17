# Runbook: Disco cheio em servidor Linux

## Quando acionar este runbook
- Alerta de uso de disco acima de 90% no Grafana/Prometheus
- Usuário reportando erro "No space left on device"
- Aplicações falhando ao gravar logs ou arquivos temporários

## Diagnóstico inicial

### 1. Identificar partições cheias
Execute para ver uso geral:

```bash
df -h
```

Procure linhas com Use% acima de 90%.

### 2. Localizar os maiores arquivos e pastas
Para descobrir o que está consumindo espaço:

```bash
du -ah / | sort -rh | head -20
```

Alternativa focada em /var (onde logs geralmente explodem):

```bash
du -ah /var | sort -rh | head -20
```

### 3. Verificar logs antigos
Logs do systemd que podem ser limpos:

```bash
journalctl --disk-usage
```

## Procedimento de limpeza

### A) Limpar logs do journal (seguro)
Manter apenas os últimos 7 dias:

```bash
journalctl --vacuum-time=7d
```

Ou limitar o tamanho total para 500MB:

```bash
journalctl --vacuum-size=500M
```

### B) Limpar cache de pacotes
Em Debian/Ubuntu:

```bash
apt-get clean
apt-get autoremove -y
```

Em RHEL/CentOS:

```bash
yum clean all
```

### C) Remover arquivos temporários antigos
Arquivos em /tmp com mais de 30 dias:

```bash
find /tmp -type f -atime +30 -delete
```

AVISO: Nunca execute isso em / sem -type f. Pode apagar diretórios essenciais.

### D) Identificar logs gigantes específicos
Procurar arquivos maiores que 500MB:

```bash
find /var/log -type f -size +500M -exec ls -lh {} \;
```

Para truncar (esvaziar sem deletar) um log:

```bash
truncate -s 0 /var/log/arquivo-gigante.log
```

## Pós-limpeza

### 1. Confirmar espaço liberado

```bash
df -h
```

### 2. Reiniciar serviços críticos (se necessário)

```bash
systemctl restart rsyslog
systemctl restart nginx
```

### 3. Ajustar rotação de logs (prevenção)
Edite /etc/logrotate.d/ para os logs problemáticos, garantindo:
- Rotação diária
- Compressão
- Retenção máxima de 30 dias

## Quando escalar
- Se após limpeza o uso voltar a ficar acima de 90% em menos de 24h
- Se houver suspeita de vazamento de memória ou disco em aplicação
- Se / estiver em partição sem espaço para resize