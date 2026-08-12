import { useEffect, useState } from 'react';
import { getStudents } from './api';

export default function useStudents(dbPath, refreshKey) {
  const [students, setStudents] = useState([]);

  useEffect(() => {
    let cancelled = false;
    getStudents(dbPath)
      .then((data) => {
        if (!cancelled) setStudents(data);
      })
      .catch(() => {
        if (!cancelled) setStudents([]);
      });
    return () => {
      cancelled = true;
    };
  }, [dbPath, refreshKey]);

  return students;
}
