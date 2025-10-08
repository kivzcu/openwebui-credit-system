from fastapi import APIRouter, HTTPException, Depends, Request, Response
import json
from pydantic import BaseModel, EmailStr, constr
from app.database import db
from app.auth import get_current_admin_user, User

router = APIRouter()


class WaitingListRegister(BaseModel):
    full_name: constr(min_length=1)
    email: EmailStr
    password: constr(min_length=8)


@router.post("/waiting-list/register", tags=["waiting_list"])
async def register_waiting_list(entry: WaitingListRegister):
    # Store plaintext password as requested (insecure) so it can be imported elsewhere
    success = db.add_waiting_list_entry(entry.full_name.strip(), entry.email.strip().lower(), entry.password)
    if not success:
        raise HTTPException(status_code=400, detail="Email already registered or could not be saved")
    return {"status": "success", "message": "Registered to waiting list"}


@router.get("/api/credits/admin/waiting-list", tags=["waiting_list"])  # admin access only
async def list_waiting_list(limit: int = 100, offset: int = 0, current_user: User = Depends(get_current_admin_user)):
    rows = db.list_waiting_list_entries(limit=limit, offset=offset)
    return rows


@router.post("/api/credits/admin/waiting-list/{entry_id}/process", tags=["waiting_list"])
async def process_waiting_list_entry(entry_id: int, current_user: User = Depends(get_current_admin_user)):
    """Mark a waiting list entry as processed (admin only)"""
    updated = db.mark_waiting_list_processed(entry_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Waiting list entry not found or could not be processed")
    return updated


@router.get("/api/credits/admin/waiting-list/download", tags=["waiting_list"])  # admin access only
async def download_waiting_list(processed: bool | None = None, current_user: User = Depends(get_current_admin_user)):
    """Download waiting list as CSV. If `processed` is provided, filter by processed state."""
    # Fetch rows including plaintext password (admin-only export)
    rows = db.fetch_all(
        """
        SELECT id, full_name, email, password_plain, created_at, processed, processed_at
        FROM credit_waiting_list
        ORDER BY processed ASC, created_at DESC
        """
    )

    # Optionally filter by processed flag
    if processed is not None:
        rows = [r for r in rows if (r.get('processed') in (True, 1, 't')) == processed]

    # Audit log the export (admin-only)
    try:
        actor = getattr(current_user, 'username', 'unknown')
        filter_used = 'all' if processed is None else ('processed' if processed else 'unprocessed')
        # Record number of rows exported
        exported_count = len(rows)
        db.execute_query(
            "INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)",
            ('export_waiting_list', actor, f'Exported {exported_count} rows ({filter_used})', json.dumps({'count': exported_count, 'filter': filter_used}))
        )
    except Exception:
        # Don't fail the export if logging fails
        pass

    # Build CSV including plaintext password (password_plain)
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    # Header
    writer.writerow(['id', 'full_name', 'email', 'password_plain', 'created_at', 'processed', 'processed_at'])
    for r in rows:
        writer.writerow([
            r.get('id'),
            r.get('full_name') or '',
            r.get('email') or '',
            r.get('password_plain') or '',
            r.get('created_at') or '',
            r.get('processed') if r.get('processed') is not None else '',
            r.get('processed_at') or ''
        ])

    csv_data = output.getvalue()
    # Suggest a filename based on filter
    if processed is None:
        fname = 'waiting_list_all.csv'
    else:
        fname = 'waiting_list_processed.csv' if processed else 'waiting_list_unprocessed.csv'

    headers = {'Content-Disposition': f'attachment; filename="{fname}"'}
    return Response(content=csv_data, media_type='text/csv', headers=headers)


@router.post('/api/credits/admin/waiting-list/cleanup', tags=['waiting_list'])
async def cleanup_migrated_waiting_list(action: str = 'delete', current_user: User = Depends(get_current_admin_user)):
    """Admin endpoint to clean up migrated waiting-list entries.
    action=delete -> delete rows where password_plain is set
    action=clear  -> clear password_plain column (set to empty string) for rows where set
    Returns a small JSON summary and writes an audit log.
    """
    import json

    action = (action or 'delete').lower()
    try:
        if action == 'clear':
            if db.db_type == 'postgresql':
                db.execute_query("UPDATE credit_waiting_list SET password_plain = '' WHERE password_plain IS NOT NULL AND password_plain <> ''", ())
            else:
                db.execute_query("UPDATE credit_waiting_list SET password_plain = ? WHERE password_plain IS NOT NULL AND password_plain <> ''", ('',))
            msg = 'Cleared password_plain for migrated rows'
        else:
            # Default action: delete migrated rows
            if db.db_type == 'postgresql':
                db.execute_query("DELETE FROM credit_waiting_list WHERE password_plain IS NOT NULL AND password_plain <> ''", ())
            else:
                db.execute_query("DELETE FROM credit_waiting_list WHERE password_plain IS NOT NULL AND password_plain <> ''", ())
            msg = 'Deleted migrated waiting-list rows'

        # Audit
        try:
            db.execute_query("INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)",
                             ('cleanup_waiting_list', getattr(current_user, 'username', 'unknown'), msg, json.dumps({'action': action})))
        except Exception:
            pass

        return {'status': 'success', 'message': msg}
    except Exception as e:
        try:
            db.execute_query("INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)",
                             ('cleanup_waiting_list_error', getattr(current_user, 'username', 'unknown'), f'Cleanup failed: {e}', json.dumps({'action': action, 'error': str(e)})))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail='Cleanup failed')


@router.post('/api/credits/admin/waiting-list/clear-hashes', tags=['waiting_list'])
async def clear_waiting_list_hashes(current_user: User = Depends(get_current_admin_user)):
    """Admin endpoint: clear password_hash values without deleting rows.
    This will set password_hash to NULL where possible, or empty string as fallback.
    If the column doesn't exist, returns ok.
    """
    import json
    try:
        # Check column existence
        col_exists = False
        if db.db_type == 'postgresql':
            res = db.fetch_one("SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s", ('credit_waiting_list', 'password_hash'))
            col_exists = bool(res)
        else:
            # SQLite: PRAGMA table_info
            try:
                info = db.fetch_all("PRAGMA table_info(credit_waiting_list)")
                col_exists = any(c.get('name') == 'password_hash' for c in info)
            except Exception:
                col_exists = False

        if not col_exists:
            return {'status': 'ok', 'message': 'password_hash column not present'}

        # Count affected rows
        count_row = db.fetch_one("SELECT COUNT(*) as cnt FROM credit_waiting_list WHERE password_hash IS NOT NULL AND password_hash <> ''")
        affected = int(count_row.get('cnt') if count_row and count_row.get('cnt') is not None else 0)

        if affected == 0:
            return {'status': 'ok', 'message': 'No hashed passwords to clear', 'affected': 0}

        # Try to set to NULL first
        try:
            if db.db_type == 'postgresql':
                db.execute_query("UPDATE credit_waiting_list SET password_hash = NULL WHERE password_hash IS NOT NULL AND password_hash <> ''", ())
            else:
                db.execute_query("UPDATE credit_waiting_list SET password_hash = NULL WHERE password_hash IS NOT NULL AND password_hash <> ''", ())
        except Exception:
            # Fallback to empty string
            try:
                if db.db_type == 'postgresql':
                    db.execute_query("UPDATE credit_waiting_list SET password_hash = '' WHERE password_hash IS NOT NULL AND password_hash <> ''", ())
                else:
                    db.execute_query("UPDATE credit_waiting_list SET password_hash = ? WHERE password_hash IS NOT NULL AND password_hash <> ''", ('',))
            except Exception as e:
                try:
                    db.execute_query("INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)", ('clear_hashes_error', getattr(current_user, 'username', 'unknown'), f'Failed to clear password_hash: {e}', json.dumps({'error': str(e)})))
                except Exception:
                    pass
                raise HTTPException(status_code=500, detail='Failed to clear hashed passwords')

        # Audit
        try:
            db.execute_query("INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)", ('clear_hashed_passwords', getattr(current_user, 'username', 'unknown'), f'Cleared {affected} password_hash values', json.dumps({'affected': affected})))
        except Exception:
            pass

        return {'status': 'success', 'message': f'Cleared password_hash for {affected} rows', 'affected': affected}
    except Exception as e:
        try:
            db.execute_query("INSERT INTO credit_logs (log_type, actor, message, metadata) VALUES (%s, %s, %s, %s)", ('clear_hashed_passwords_error', getattr(current_user, 'username', 'unknown'), f'Failed clearing hashed passwords: {e}', json.dumps({'error': str(e)})))
        except Exception:
            pass
        raise HTTPException(status_code=500, detail='Error clearing hashed passwords')
