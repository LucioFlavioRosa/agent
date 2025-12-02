# Azure Cache for Redis: Configuração de Endpoint Privado e Subrede

Este guia explica como configurar o Azure Cache for Redis em uma subrede privada, garantindo que o acesso seja permitido apenas ao App Service via Private Endpoint.

## 1. Criação da Subrede e Private Endpoint
- No portal do Azure, crie uma subrede dedicada para o Redis.
- Crie o recurso Azure Cache for Redis e selecione a opção de rede virtual (VNET).
- Adicione um Private Endpoint para o Redis, associando-o à subrede criada.

## 2. Configuração do App Service (VNET Integration)
- No App Service, habilite a integração com VNET.
- Selecione a mesma subrede onde o Private Endpoint do Redis está configurado.
- Certifique-se de que o App Service tem permissão para acessar a subrede.

## 3. Variáveis de Ambiente e Segurança
- Defina as variáveis de ambiente no App Service:
  - `REDIS_HOST`: endpoint privado do Redis (exemplo: `your-redis-cache.redis.cache.windows.net`)
  - `REDIS_PORT`: use `6380` para conexão SSL/TLS
  - `REDIS_USE_SSL`: `True`
  - `REDIS_SSL_CERT_REQS`: `required`
- O Redis só será acessível pelo App Service, não por IPs externos.

## 4. Validação de Conectividade
- Garanta que o backend está usando SSL/TLS ao conectar ao Redis.
- O pacote `redis>=4.5.0` deve ser utilizado para compatibilidade com SSL.
- Teste a conexão usando o endpoint privado e verifique se não há acesso externo.

## 5. Exemplos de Comandos Azure CLI
bash
az network vnet subnet create --resource-group <rg> --vnet-name <vnet> --name <subnet-redis> --address-prefixes <prefix>
az redis create --name <redis-name> --resource-group <rg> --sku Premium --subnet-id <subnet-id>
az network private-endpoint create --name <pe-redis> --resource-group <rg> --vnet-name <vnet> --subnet <subnet-redis> --private-connection-resource-id <redis-id> --group-ids redisCache


## 6. Observações
- O App Service deve estar na mesma VNET/subrede do Redis.
- O backend deve ser configurado para usar SSL/TLS obrigatoriamente.
- Não é possível acessar o Redis de fora da subrede; apenas o App Service terá acesso.
