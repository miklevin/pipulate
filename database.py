
def get_db_filename():
    current_env = get_current_environment()
    if current_env == 'Development':
        return f'data/{APP_NAME.lower()}_dev.db'
    else:
        return f'data/{APP_NAME.lower()}.db'

DB_FILENAME = get_db_filename()

def db_operation(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            if func.__name__ == '__setitem__':
                key, value = (args[1], args[2])
                if not key.startswith('_') and (not key.endswith('_temp')):
                    if key in ('last_app_choice', 'last_profile_id', 'last_visited_url', 'pipeline_id'):
                        log.data(f'State updated: {key}', value)
                    else:
                        log.debug('database', f'DB {func.__name__}: {key}', f'value: {str(value)[:30]}...' if len(str(value)) > 30 else f'value: {value}')
            return result
        except Exception as e:
            # Don't log KeyError as ERROR for __getitem__ - it's expected behavior
            if func.__name__ == '__getitem__' and isinstance(e, KeyError):
                logger.debug(f'Key not found in database: {e}')
            else:
                log.error(f'Database operation {func.__name__} failed', e)
            raise
    return wrapper

class DictLikeDB:

    def __init__(self, store, Store):
        self.store = store
        self.Store = Store
        logger.debug('DictLikeDB initialized.')

    @db_operation
    def __getitem__(self, key):
        try:
            value = self.store[key].value
            logger.debug(f'Retrieved from DB: {key} = {value}')
            return value
        except NotFoundError:
            # Don't log as error - this is expected behavior when checking for keys
            logger.debug(f'Key not found: {key}')
            raise KeyError(key)

    @db_operation
    def __setitem__(self, key, value):
        try:
            self.store.update({'key': key, 'value': value})
            logger.debug(f'Updated persistence store: {key} = {value}')
        except NotFoundError:
            self.store.insert({'key': key, 'value': value})
            logger.debug(f'Inserted new item in persistence store: {key} = {value}')

    @db_operation
    def __delitem__(self, key):
        try:
            self.store.delete(key)
            if key != 'temp_message':
                logger.warning(f'Deleted key from persistence store: {key}')
        except NotFoundError:
            logger.error(f'Attempted to delete non-existent key: {key}')
            raise KeyError(key)

    @db_operation
    def __contains__(self, key):
        exists = key in self.store
        logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' exists: <{COLOR_MAP['value']}>{exists}</{COLOR_MAP['value']}>")
        return exists

    @db_operation
    def __iter__(self):
        for item in self.store():
            yield item.key

    @db_operation
    def items(self):
        for item in self.store():
            yield (item.key, item.value)

    @db_operation
    def keys(self):
        return list(self)

    @db_operation
    def values(self):
        for item in self.store():
            yield item.value

    @db_operation
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            logger.debug(f"Key '<{COLOR_MAP['key']}>{key}</{COLOR_MAP['key']}>' not found. Returning default: <{COLOR_MAP['value']}>{default}</{COLOR_MAP['value']}>")
            return default

    @db_operation
    def set(self, key, value):
        self[key] = value
        return value

db = DictLikeDB(store, Store)

def populate_initial_data():
    """Populate initial data in the database."""
    if TABLE_LIFECYCLE_LOGGING:
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Starting.')
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles BEFORE')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db BEFORE')
    if not profiles():
        default_profile_name_for_db_entry = 'Default Profile'
        existing_default_list = list(profiles('name=?', (default_profile_name_for_db_entry,)))
        if not existing_default_list:
            default_profile_data = {'name': default_profile_name_for_db_entry, 'real_name': 'Default User', 'address': '', 'code': '', 'active': True, 'priority': 0}
            default_profile = profiles.insert(default_profile_data)
            logger.debug(f'Inserted default profile: {default_profile} with data {default_profile_data}')
            if default_profile and hasattr(default_profile, 'id'):
                db['last_profile_id'] = str(default_profile.id)
                logger.debug(f'Set last_profile_id to new default: {default_profile.id}')
            else:
                logger.error('Failed to retrieve ID from newly inserted default profile.')
        else:
            logger.debug(f"Default profile named '{default_profile_name_for_db_entry}' already exists. Skipping insertion.")
            if 'last_profile_id' not in db and existing_default_list:
                db['last_profile_id'] = str(existing_default_list[0].id)
                logger.debug(f'Set last_profile_id to existing default: {existing_default_list[0].id}')
    elif 'last_profile_id' not in db:
        first_profile_list = list(profiles(order_by='priority, id', limit=1))
        if first_profile_list:
            db['last_profile_id'] = str(first_profile_list[0].id)
            logger.debug(f'Set last_profile_id to first available profile: {first_profile_list[0].id}')
        else:
            logger.warning("No profiles exist and 'last_profile_id' was not set. This might occur if default creation failed or DB is empty.")
    if 'last_app_choice' not in db:
        db['last_app_choice'] = ''
        logger.debug('Initialized last_app_choice to empty string')
    if 'current_environment' not in db:
        db['current_environment'] = 'Development'
        logger.debug("Initialized current_environment to 'Development'")
    if 'profile_locked' not in db:
        db['profile_locked'] = '0'
        logger.debug("Initialized profile_locked to '0'")
    if 'split-sizes' not in db:
        db['split-sizes'] = '[65, 35]'  # Default split panel sizes
        logger.debug("Initialized split-sizes to default '[65, 35]'")
    if 'theme_preference' not in db:
        db['theme_preference'] = 'auto'  # Default theme preference
        logger.debug("Initialized theme_preference to 'auto'")
    if 'intro_current_page' not in db:
        db['intro_current_page'] = '1'  # Default to page 1 of introduction
        logger.debug("Initialized intro_current_page to '1'")
    if TABLE_LIFECYCLE_LOGGING:
        log_dynamic_table_state('profiles', lambda: profiles(), title_prefix='POPULATE_INITIAL_DATA: Profiles AFTER')
        log_dictlike_db_to_lifecycle('db', db, title_prefix='POPULATE_INITIAL_DATA: db AFTER')
        logger.bind(lifecycle=True).info('POPULATE_INITIAL_DATA: Finished.')
