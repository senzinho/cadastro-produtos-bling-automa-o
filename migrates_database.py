"""
Script de Migração do Banco de Dados
Execute este script ANTES de rodar o app.py
"""

import pymysql
from datetime import datetime

# Configurações do banco - AJUSTE SE NECESSÁRIO
DB_CONFIG = {
    'host': 'localhost',
    'user': 'policia',
    'password': 'Saopio22.20305',
    'database': 'controle_acessos',
    'charset': 'utf8mb4'
}

def check_column_exists(cursor, table_name, column_name):
    """Verifica se uma coluna existe na tabela"""
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{DB_CONFIG['database']}' 
        AND TABLE_NAME = '{table_name}' 
        AND COLUMN_NAME = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

def migrate_database():
    """Executa a migração do banco de dados"""
    try:
        print('='*70)
        print('🔧 INICIANDO MIGRAÇÃO DO BANCO DE DADOS')
        print('='*70)
        
        # Conecta ao banco
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print(f'✅ Conectado ao banco: {DB_CONFIG["database"]}')
        
        # Migração 1: Adicionar email_attempt à tabela login_history
        if not check_column_exists(cursor, 'login_history', 'email_attempt'):
            print('\n📝 Adicionando coluna email_attempt...')
            cursor.execute("""
                ALTER TABLE login_history 
                ADD COLUMN email_attempt VARCHAR(100) AFTER user_id
            """)
            connection.commit()
            print('✅ Coluna email_attempt adicionada!')
        else:
            print('\n✓ Coluna email_attempt já existe')
        
        # Migração 2: Adicionar user_agent à tabela login_history
        if not check_column_exists(cursor, 'login_history', 'user_agent'):
            print('\n📝 Adicionando coluna user_agent...')
            cursor.execute("""
                ALTER TABLE login_history 
                ADD COLUMN user_agent VARCHAR(255) AFTER ip_address
            """)
            connection.commit()
            print('✅ Coluna user_agent adicionada!')
        else:
            print('\n✓ Coluna user_agent já existe')
        
        # Verifica a estrutura final
        print('\n📊 Estrutura da tabela login_history:')
        cursor.execute("DESCRIBE login_history")
        columns = cursor.fetchall()
        for col in columns:
            print(f'   • {col[0]} ({col[1]})')
        
        # Mostra algumas entradas
        print('\n📋 Últimas entradas no histórico de login:')
        cursor.execute("""
            SELECT id, user_id, email_attempt, success, created_at 
            FROM login_history 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        entries = cursor.fetchall()
        
        if entries:
            for entry in entries:
                print(f'   • ID: {entry[0]}, User: {entry[1]}, Email: {entry[2]}, Sucesso: {entry[3]}, Data: {entry[4]}')
        else:
            print('   (Nenhuma entrada encontrada)')
        
        cursor.close()
        connection.close()
        
        print('\n' + '='*70)
        print('✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!')
        print('='*70)
        print('💡 Agora você pode executar o app.py normalmente')
        print('='*70 + '\n')
        
        return True
        
    except pymysql.Error as e:
        print(f'\n❌ Erro na migração: {e}')
        return False
    except Exception as e:
        print(f'\n❌ Erro inesperado: {e}')
        return False

if __name__ == '__main__':
    success = migrate_database()
    
    if not success:
        print('\n⚠️  A migração falhou. Verifique:')
        print('   1. O MySQL está rodando?')
        print('   2. As credenciais estão corretas?')
        print('   3. O banco "controle_acessos" existe?')
        print('\n💡 Você também pode executar o script SQL manualmente.')
        exit(1)
    
    exit(0)