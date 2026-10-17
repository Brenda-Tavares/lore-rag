# Runbook: Reiniciar servidor Apache

## Diagnóstico
Quando o Apache não responde na porta 80.

## Procedimento
1. Verificar status: systemctl status apache2
2. Testar configuração: apache2ctl configtest
3. Reiniciar: systemctl restart apache2

## Verificação
Acessar curl localhost deve retornar HTML padrão.